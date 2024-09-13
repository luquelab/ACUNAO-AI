from typing import Optional, List, Any
import io
from pathlib import Path
import pymupdf
from PIL import Image
from pydantic import BaseModel
import cv2
import numpy as np
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers.string import StrOutputParser
import os
from transformers import pipeline, AutoProcessor, VisionEncoderDecoderModel, StoppingCriteria, StoppingCriteriaList
import torch
from collections import defaultdict
import re


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
    
class RunningVarTorch: 
    def __init__(self, L=15, norm=False):
        self.values = None
        self.L = L
        self.norm = norm

    def push(self, x: torch.Tensor):
        assert x.dim() == 1
        if self.values is None: 
            self.values = x[:, None]
        elif self.values.shape[1] < self.L:
            self.values = torch.cat((self.values, x[:, None]), 1)
        else:
            self.values = torch.cat((self.values[:, 1:], x[:, None]), 1)

    def variance(self):
        if self.values is None:
            return
        if self.norm:
            return torch.var(self.values, 1) / self.values.shape[1]
        else:
            return torch.var(self.values, 1)
        
class StoppingCriteriaScores(StoppingCriteria):
    def __init__(self, threshold: float = 0.015, window_size: int = 200):
        super().__init__()
        self.threshold = threshold
        self.vars = RunningVarTorch(norm=True)
        self.varvars = RunningVarTorch(L=window_size)
        self.stop_inds = defaultdict(int)
        self.stopped = defaultdict(bool)
        self.size = 0
        self.window_size = window_size

    @torch.no_grad()
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor):
        last_scores = scores[-1]
        self.vars.push(last_scores.max(1)[0].float().cpu())
        self.varvars.push(self.vars.variance())
        self.size += 1
        if self.size < self.window_size:
            return False

        varvar = self.varvars.variance()
        for b in range(len(last_scores)):
            if varvar[b] < self.threshold:
                if self.stop_inds[b] > 0 and not self.stopped[b]:
                    self.stopped[b] = self.stop_inds[b] >= self.size
                else:
                    self.stop_inds[b] = int(
                        min(max(self.size, 1) * 1.15 + 150 + self.window_size, 4095)
                    )
            else:
                self.stop_inds[b] = 0
                self.stopped[b] = False
        return all(self.stopped.values()) and len(self.stopped) > 0
    
    
class PDFLoader:
    """
    Load PDF to a custom document element format for vector databases.

    Args:
        pdf_path (Path): The path to the PDF file.

    Attributes:
        elements: Document elements to add to vector databases.
        pipe: Initiate table-transformer-detection.
    """
    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.elements = []
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.processor_noug = AutoProcessor.from_pretrained("facebook/nougat-small")
        self.model_noug = VisionEncoderDecoderModel.from_pretrained("facebook/nougat-small")

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
            im = Image.open(image)
            pixel_values = self.processor_noug(images=im, return_tensors="pt").pixel_values
            outputs = self.model_noug.generate(pixel_values.to(self.device),
                                min_length=1,
                                max_length=3584,
                                bad_words_ids=[[self.processor_noug.tokenizer.unk_token_id]],
                                return_dict_in_generate=True,
                                output_scores=True,
                                stopping_criteria=StoppingCriteriaList([StoppingCriteriaScores()]),)
            generated = self.processor_noug.batch_decode(outputs[0], skip_special_tokens=True)[0]
            generated = self.processor_noug.post_process_generation(generated, fix_markdown=False)
            metadata = {"source": filepath, "page": i}
            self.elements.append(Element(type="text", page_content=generated, metadata=metadata))
            print("Text appended")

        for ele in self.elements:
            if ele.type == "text":
                text = ele.page_content
                pattern = r'(\\begin{tabular}(.*?)\\end{tabular})'
                matches = re.findall(pattern, text, re.DOTALL)
                if matches:
                    for match in matches:
                        txt = text.replace(match[0], "")
                        self.elements.append(Element(type="table", page_content=match[0].strip(), metadata=ele.metadata))
                        ele.page_content = txt
                        print("Table appended")

    def summarize_tables(self):
        llm = ChatOllama(model="phi3:medium-128k", temperature=0)
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

    def create_overlapping_pages(self, overlap_size=1000):
        num_elements = len(self.elements)

        for i in range(num_elements - 1):
            if self.elements[i].metadata["source"] == "text":
                current_page_content = self.elements[i].page_content
                next_page_content = self.elements[i + 1].page_content
                overlap_content = next_page_content[:overlap_size]
                combined_content = current_page_content + ' ' + overlap_content
                self.elements[i].page_content = combined_content