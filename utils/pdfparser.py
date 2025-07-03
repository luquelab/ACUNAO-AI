from typing import Optional, List, Any
import io
from pathlib import Path
import pymupdf
from PIL import Image
from pydantic import BaseModel
import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from langchain_community.chat_models import ChatLlamaCpp
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers.string import StrOutputParser
import os
from transformers import pipeline
import torch
from utils.embeddings import initialize_embeddings_and_db
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Comment the following out when making changes locally
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ["TESSDATA_PREFIX"] = r"C:\Program Files\Tesseract-OCR\tessdata"

os.environ["TOKENIZERS_PARALLELISM"] = "false"

class Element(BaseModel):
    # Custom document elements for loader
    type: str
    page_content: Any
    metadata: dict

def rasterize_paper(
    pdf: Path,
    outpath: Optional[Path] = None,
    dpi: int = 300,
    return_pil=False,
    pages=None,
) -> Optional[List[io.BytesIO]]:
    """
    Rasterize a PDF file to PNG images.

    Args:
        pdf (Path): The path to the PDF file.
        outpath (Optional[Path], optional): The output directory. If None, the PIL images will be returned instead. Defaults to None.
        dpi (int, optional): The output DPI. Defaults to 300.
        return_pil (bool, optional): Whether to return the PIL images instead of writing them to disk. Defaults to False.
        pages (Optional[List[int]], optional): The pages to rasterize. If None, all pages will be rasterized. Defaults to None.

    Returns:
        Optional[List[io.BytesIO]]: The PIL images if `return_pil` is True, otherwise None.
    """
    pillow_images = []
    if outpath is None:
        return_pil = True
    try:
        with pymupdf.open(pdf) as pdf_doc:
            if pages is None:
                pages = range(len(pdf_doc))
            for i in pages:
                page_bytes = pdf_doc[i].get_pixmap(dpi=dpi).tobytes("png")
                if return_pil:
                    pillow_images.append(io.BytesIO(page_bytes))
                else:
                    outpath.mkdir(parents=True, exist_ok=True)
                    with (outpath / f"{i + 1:02d}.png").open("wb") as f:
                        f.write(page_bytes)
    except Exception as e:
        print(f"Error rasterizing PDF: {e}")
        return None

    if return_pil:
        return pillow_images, pdf
    
    
class PDFLoader:
    """
    Load PDF to a custom document element format for vector databases.

    Args:
        pdf_path (Path): The path to the PDF file.

    Attributes:
        pdf_path: Path to the pdf to be processed.
        elements: Document elements to add to vector databases.
        device: Type of device, cuda or cpu.
        pipe: Initiate table-transformer-detection.
        db: Name of database.
        client: Initiated vector database client.
        vectordb: Initiated vector database.
        text_splitter: Initiated text splitter.
        llm_model: Initiated path to the llm model.
    """
    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.elements = []
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.pipe = pipeline("object-detection", model="microsoft/table-transformer-detection", device=self.device)
        # Initialize embeddings and vector database
        self.db="project_example"
        _, self.client, self.vectordb, self.text_splitter, self.llm_model = initialize_embeddings_and_db(self.db)
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=4500, 
                                                            chunk_overlap=1000
                                                            )

    def load(self):
        images, filepath = rasterize_paper(self.pdf_path, return_pil=True)
        if images is None:
            print("Failed to rasterize PDF.")
            return []

        self.extract(images, filepath)
        print("elements stored")
        self.create_overlapping_pages(1000)
        print("elements overlapped")
        self.summarize_tables()
        print("tables summarized")

        return self.elements

    def extract(self, images, filepath):
        """
        Extract tables and texts from all images.
        """

        for i, image in enumerate(images):
            metadata = {"source": str(filepath), "page": i+1}
            image = Image.open(image).convert("RGB")
            results = self.pipe(image)
            image = np.array(image)

            boxes = []

            for result in results:
                if result["label"] == "table" and result["score"] > 0.95:
                    box = [result["box"]['xmin']-15, result["box"]['ymin']-15, result["box"]['xmax']+15, result["box"]['ymax']+15]
                    boxes.append(box)
                    print("boxes appended")

                    im = image[box[1]:box[3], box[0]:box[2]]
                    print("image cropped")

                    # Preprocess the image for OCR
                    im = cv2.resize(np.array(im), None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
                    im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
                    kernel = np.ones((1, 1), np.uint8)
                    im = cv2.dilate(im, kernel, iterations=1)
                    im = cv2.erode(im, kernel, iterations=1)
                    im = cv2.threshold(cv2.medianBlur(im, 3), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

                    # Configure and conduct OCR
                    custom_config = r'--oem 3 --psm 4'
                    table_txt = pytesseract.image_to_string(im, config=custom_config, lang="eng")

                    # Remove table from image
                    cv2.rectangle(image, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (255,255,255), -1)

                    self.elements.append(Element(type="table", page_content=table_txt, metadata=metadata))
                    print("tables appended")

            custom_config = r'--oem 3 --psm 1'

            # Convert the image to grayscale
            final_img = image[200:-200]
            final_img = cv2.resize(final_img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

            # Preprocess the image for OCR
            imag = cv2.cvtColor(final_img, cv2.COLOR_BGR2GRAY)
            kernel = np.ones((1, 1), np.uint8)
            imag = cv2.dilate(imag, kernel, iterations=1)
            imag = cv2.erode(imag, kernel, iterations=1)
            imag = cv2.threshold(cv2.medianBlur(imag, 3), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            bboxes = self.get_paragraph_bounding_boxes(final_img)

            all_texts = []
            custom_config = r"--oem 3 --psm 1"
            for bbox in bboxes:
                x, y, w, h = bbox
                roi = imag[y:h, x:w]

                fin = final_img[y:h, x:w]

                if fin.shape[0] > 0 and fin.shape[1] > 0:
                    # Convert to grayscale and apply Otsu's threshold
                    gray = cv2.cvtColor(fin, cv2.COLOR_BGR2GRAY)
                    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
                    # Dilate with a horizontal kernel
                    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 10))
                    dilate = cv2.dilate(thresh, kernel, iterations=2)
                    # Find contours
                    cnts = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cnts = cnts[0] if len(cnts) == 2 else cnts[1]

                    contours_found = False
                    for c in cnts:
                        x, y, w, h = cv2.boundingRect(c)
                        area = cv2.contourArea(c)
                        if w/h > 2 and area > 10000:
                            contours_found = True  
                        else:
                            pass
                    
                    if contours_found:
                        text = pytesseract.image_to_string(roi, config=custom_config, lang="eng").replace("\n", " ")
                        cleaned = text
                        cleaned = ''.join(e for e in cleaned if e.isalnum())
                        if cleaned.isdigit():
                            pass
                        else:
                            all_texts.append(text)
                    else:
                        pass
                else:
                    pass

            all_text = "\n".join(all_texts)

            # Detect and exclude references
            citation_patterns = [r'\[\d+\]', r'\d+\.', r'(\bdoi\b|\bdoi.org\b|arxiv|vol|issn|isbn|et al\.)']
            citation_regex = re.compile('|'.join(citation_patterns), re.IGNORECASE)

            # Remove text identified as references
            text_without_references = []
            for line in all_text.split("\n"):
                if not citation_regex.search(line): 
                    text_without_references.append(line)

            # Combine filtered text
            filtered_text = "\n".join(text_without_references)

            chunks = self.text_splitter.split_text(filtered_text)

            for chunk in chunks:
                self.elements.append(Element(type="text", page_content=chunk, metadata=metadata))
                print("text appended")
            
            print("page appended")
            

    def summarize_tables(self):
        llm = ChatLlamaCpp(
            model_path = self.llm_model,
            n_gpu_layers = -1, 
            n_batch = 256,
            f16_kv = True,
            temperature = 0.0,
            verbose = True,
            n_ctx = 5028,
            max_tokens=1048
        )
        prompt_text = """
        You are an assistant tasked with summarizing tables. \n 
        Give a detailed summary of the table. Do not use your pre-conceived notion and summarize exclusively with the information in the table. It is very important that you only provide the final output without any additional comments or remarks. Table: {element} 
        """
        prompt = ChatPromptTemplate.from_template(prompt_text)
        summarize_chain = {"element": lambda x: x} | prompt | llm | StrOutputParser()

        for element in self.elements:
            if element.type == "table":
                summary = summarize_chain.invoke({"element": str(element.page_content)})
                element.page_content = summary

    def get_paragraph_bounding_boxes(self, image):
        # Perform OCR using Tesseract
        custom_config = r'--oem 3 --psm 1'
        data = pytesseract.image_to_data(image, output_type=Output.DICT, config=custom_config)
        
        # Get bounding boxes
        n_boxes = len(data['level'])
        bounding_boxes = []
        for i in range(1, n_boxes):
            (x, y, w, h) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
            bounding_boxes.append((x, y, x + w, y + h))
        
        # Merge overlapping boxes
        def merge_boxes(boxes):
            if not boxes:
                return []
            
            boxes = sorted(boxes, key=lambda b: b[1])  # Sort by top coordinate
            merged_boxes = [boxes[0]]
            
            for current in boxes:
                last = merged_boxes[-1]
                if current[1] <= last[3]:  # Overlapping boxes
                    merged_boxes[-1] = (min(last[0], current[0]), min(last[1], current[1]),
                                        max(last[2], current[2]), max(last[3], current[3]))
                else:
                    merged_boxes.append(current)
            
            return merged_boxes
        
        paragraphs = merge_boxes(bounding_boxes)
        
        return paragraphs

    def create_overlapping_pages(self, overlap_size=1000):
        num_elements = len(self.elements)

        for i in range(num_elements - 1):
            if self.elements[i].metadata["source"] == "text":
                current_page_content = self.elements[i].page_content
                next_page_content = self.elements[i + 1].page_content
                overlap_content = next_page_content[:overlap_size]
                combined_content = current_page_content + ' ' + overlap_content
                self.elements[i].page_content = combined_content