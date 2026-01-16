import os
import gc
from datetime import datetime
from PIL import Image
import fitz
import tempfile
import io
import time
from pathlib import Path
import shutil
import base64
from tqdm import tqdm
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
import openai
from ETL.document_processor.base.models import complete_doc


Image.MAX_IMAGE_PIXELS = None

class etl_components:
    """Processes images."""

    def __init__(self, file, llm_multimodal):
        """
        Initialize etl_components.

        Args:
        - file (str): Image file path.
        - bucket_name (str, optional): Name of the Google Cloud Storage bucket (default: False).
        """
        self.file = file
        self.llm_multimodal = llm_multimodal


    def pdf_to_base64_utf8_images(self,blob_pdf_path=False):
        # Open the PDF file
        pdf_document = fitz.open(self.file)

        # List to store base64 encoded images
        base64_images = []
        raw_images = []
        images_path = []
        images_path_blob = []
        names=[]

        # Ensure the output folder exists
        temp_dir=tempfile.mkdtemp()+"/"

        try:
            # Iterate over each page
            for page_num in range(len(pdf_document)):
                # Get the page
                page = pdf_document.load_page(page_num)

                # Render the page to an image
                pix = page.get_pixmap(dpi=300)

                # Convert the image to PIL Image format
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                raw_images.append(img)

                # Save the image to a BytesIO object in JPEG format
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')

                ##### For image source - blob storage
                if blob_pdf_path != False:
                    blob_image_full_path = os.path.join(os.path.dirname(blob_pdf_path),f"{Path(self.file).stem}_{page_num + 1}.jpeg")
                    images_path_blob.append(blob_image_full_path)



                ##### local images path
                images_location_locally = os.path.join(temp_dir, f"{Path(self.file).stem}_{page_num + 1}.jpeg")
                images_path.append(images_location_locally)
                names.append(Path(images_location_locally).stem)
                #####


                # Get the byte data of the image
                img_byte_arr = img_byte_arr.getvalue()

                # Encode the byte data to base64
                img_base64 = base64.b64encode(img_byte_arr)

                # Encode the base64 bytes to UTF-8 string
                img_base64_utf8 = img_base64.decode('utf-8')

                # Append the UTF-8 string to the list
                base64_images.append(img_base64_utf8)
                imagestring_n_name = dict(zip(names,base64_images))

                del img_byte_arr
                del img_base64_utf8
                del img
                del img_base64
                del page

                gc.collect()

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return (imagestring_n_name)


    def summarize_image(self,encoded_image: str) -> str:
        """
        Asynchronous Summarize the content of the provided image using an LLM.

        Args:
            encoded_image (str): Base64-encoded image string.

        Returns:
            str: Summarized content of the image.
        """
        prompt = [
            SystemMessage(content="""You are a bot that is good at analyzing images. Please act as an Expert and help in analysing and describing the tables, flowcharts, graphs, plots etc. 
                          Please extract all the details given in the image.\n Use only these images."""),
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": """Execute the following tasks step by step and extract information.
                    1. Capture the maximum possible details (all the details) given in the image in a best possible way.
                    2. Wherever text is present, extract ALL the text as it is without changing/modifying the text. 
                    In Image, if plots, diagrams, tables present please provide description and capture as much as details possible (note: some images has image caption). Please elaborate captions and other additional details also.
                    3. Please examine the each step of flowcharts and process flow carefully and describe them step by step in detail.
                    Please capture all the possible details.
                    4. Please also capture facts and numeric information given in plots and graphs such barplot, histogram, lineplot etc
                    5. Please also capture exact text given on different objects or products and also capture details of given entities.
                    6. Please also capture information such as references, information given on header, footers, filenames,
                    page, question, answers, multiple choice questions, signatures, signatory names and other additional information etc.
                    7. Carefully, capture the exact text and details given on different tables and extract it in markdown structured table format.
                    Please do it extremely carefully and in detail.

                    # Provide all the extracted details in the best way possible in Markdown format (headings, Subheadings, text, points etc).
                    # Please avois writing extra text such as Extracted Information from the Image. You can directly start from content. 
                    
                    Take a deep breath and let's do it step by step. It is important for my career!"""

                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{encoded_image}"
                    },
                },
            ])
        ]


        retries = 0
        max_retries = 10
        while retries < max_retries:

            try:
                response = self.llm_multimodal.invoke(prompt)
                return response.content
            
            except openai.error.InvalidRequestError as e:
                if e.error.code == "content_filter" and e.error.innererror:
                    content_filter_result = e.error.innererror.content_filter_result
                    # print the formatted JSON
                    print(content_filter_result)
                    # or access the individual categories and details
                    for category, details in content_filter_result.items():
                        print(f"{category}:\n filtered={details['filtered']}\n severity={details['severity']}")

            except Exception as e:
                if "limit" in str(e).lower():
                    print(f"Rate limit error encountered. Retrying in 30 seconds... (Attempt {retries+1}/{max_retries})")
                    retries += 1
                    time.sleep(6)

        
    def new_summarize_image(self,encoded_image: str) -> str:
        """
        Asynchronous Summarize the content of the provided image using an LLM.

        Args:
            encoded_image (str): Base64-encoded image string.

        Returns:
            str: Summarized content of the image.
        """
        prompt = [
            SystemMessage(content="""You are an expert image analysis bot. You are a bot that is good at analyzing images. Please act as an Expert and help in analysing and describing the tables, flowcharts, graphs, plots etc.
            Please extract all the details given in the image, maintaining original formatting, structure, and layout for the text.

            **CRITICAL RULES:**
            - Extract text EXACTLY as it appears in the image - preserve original formatting, line breaks, and structure.
            - Start directly with the actual content from the image.
            - Maintain the EXACT layout and format from the image for text content.

            **Tasks:**
            1. Capture the maximum possible details (all details) given in the image in the best possible way.
                          
            2. Extract ALL text as it is, without changing or modifying the text, and preserve original formatting and structure.
                          
            3. For all non-textual elements—such as flowcharts, diagrams, footers, pages, logos, visual objects, and any other graphical or layout features—provide clear, descriptive, and detailed explanations, covering every minute piece of information present.  
            - Carefully describe each component, symbol, shape, icon, color, positioning, and any visible annotation or mark.
            - If the image contains captions for these elements, elaborate on those captions and include all additional details.
                          
            4. For flowcharts and process flows: examine each step carefully and describe them step by step in detail.
                          
            5. Capture all facts and numeric information given in plots and graphs (such as bar plots, histograms, line plots, etc.).
                          
            6. Extract exact text given on different objects, products, and entities. Capture details of all given entities.
                          
            7. Capture and extract details such as references, headers, footers, filenames, page numbers, questions, answers, multiple choice questions, signatures, signatory names, and any other additional information present.
                - For elements such as dates, signatures, names, or other indicators, you may add a brief clarifying note in parentheses or as a footnote to indicate what the element is (e.g., "Date: 2023-05-01 (document creation date)", "Signature: John Doe (signatory)"), but **do NOT change or paraphrase the actual text content**.
                - If additional details about a signature, date, or other indicator are present (such as title, position, or context), include those descriptively.
          
            8. For tables: extract the exact text and details given on different tables and present them in Markdown structured table format, preserving the exact structure. Do this with extreme care and detail.

            **Output Format:**
            - Use Markdown formatting (headings, subheadings, text, points, code blocks where appropriate).
            - For text content: maintain the EXACT layout and format from the image.
            - For visual and graphical elements (charts, diagrams, flowcharts, logos, etc.): provide clear, comprehensive, and detailed descriptions, including any captions and additional details.
            - For tables: use Markdown table format, preserving the original structure and all details.

            Begin extraction immediately without preamble."""
            ),
            HumanMessage(content=[
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{encoded_image}"
                    },
                },
            ])
        ]


        retries = 0
        max_retries = 10
        while retries < max_retries:

            try:
                response = self.llm_multimodal.invoke(prompt)
                return response.content
            
            except openai.error.InvalidRequestError as e:
                if e.error.code == "content_filter" and e.error.innererror:
                    content_filter_result = e.error.innererror.content_filter_result
                    # print the formatted JSON
                    print(content_filter_result)
                    # or access the individual categories and details
                    for category, details in content_filter_result.items():
                        print(f"{category}:\n filtered={details['filtered']}\n severity={details['severity']}")

            except Exception as e:
                if "limit" in str(e).lower():
                    print(f"Rate limit error encountered. Retrying in 30 seconds... (Attempt {retries+1}/{max_retries})")
                    retries += 1
                    time.sleep(6)



    def generate_document_summary_stuff(self, image_summary_list):

        """
        Generate a document summary from a list or String content of image summaries.
        """
        if isinstance(image_summary_list, list):
            combine ='\n\n#############################################\n\n'.join(image_summary_list)
            docs=[combine]
        else:
            docs=[image_summary_list]

        doc_creator = RecursiveCharacterTextSplitter(chunk_size=1500,chunk_overlap=150,length_function=len,is_separator_regex=False)

        split_docs = doc_creator.create_documents(texts = docs)

        prompt_template_fulldocument = """
            Write a concise summary that captures the superficial overview and key points from the following text:\n{context}

            Your summary should:
            - Provide a high-level overview, focusing on the main themes and key highlights.
            - Include relevant attributes such as TITLES, SUBTITLES, COMPANY NAMES, REFERENCES, DATES, TOTAL PAGE COUNT, DOCUMENT IDs, and any other significant details.
            - Be no longer than 15-18 lines to maintain conciseness.
            - Present the information in a clear, structured, and easy-to-read manner.

            Please ensure the summary balances brevity with comprehensiveness, providing a superficial yet meaningful overview of the text.

            SUMMARY:
            """

        prompt_document = PromptTemplate.from_template(prompt_template_fulldocument)

        retries = 0
        max_retries = 10
        while retries < max_retries:

            try:
                llmchain = create_stuff_documents_chain(self.llm_multimodal, prompt_document)

                # Invoke the llm chain with the document object
                document_summaries = llmchain.invoke({"context": split_docs})

                return document_summaries

            except Exception as e:
                if "limit" in str(e).lower():
                    print(f"Rate limit error encountered. Retrying in 8 seconds... (Attempt {retries+1}/{max_retries})")
                    retries += 1
                    time.sleep(6)
                else:
                    raise e
        raise Exception("Max retries reached due to rate limit errors.")


    def append_chunks_fulldoc_summary(self, concise_doc_summary, splitted_text, file=None):
        import copy

        filename = os.path.basename(file) if file else 'Not given'

        chunk_n = copy.deepcopy(splitted_text)
        doc_summary = concise_doc_summary
        for d in range(len(chunk_n)):
            entire_summary = f'{str(chunk_n[d].page_content)}\n\n---\n\n### **Filename : {filename}** \n### Consolidated summary / high-level overview of whole document given below: ##############\n\n{str(doc_summary)}'

            chunk_n[d].page_content = entire_summary

        return chunk_n
    

    def stitch_pages(self, reference_text, page_contents_list):
        """
        Stitches together page-by-page content into a complete document.

        Args:
            reference_text (str): The original/reference text for context.
            page_contents_list (list): List of extracted content from each page.

        Returns:
            str: The stitched complete document.
        """

        stiching_template = """You are an expert document reconstruction specialist. Your task is to intelligently stitch together page-by-page extracted content into a single, coherent, and complete document.

            
        **PAGE-BY-PAGE EXTRACTED CONTENT:**
        {page_contents}

        

        Purpose of Reference to let you fill missing link between different page. Please do not consider it for any other purpose.
        **REFERENCE TEXT (Original Document - Use as Context):**
        {reference_text}


        **YOUR TASK:**
        Reconstruct the complete document by:

        1. **Connecting Split Text**: 
        - Identify sentences/paragraphs that are split across pages
        - Merge them seamlessly without duplication
        - Existing content should remain unchanged, But same time feel free to remove redundant lines.
        - Fill in minimal connector text ONLY where absolutely necessary for coherence

        2. **Merging Split Tables**:
        - Identify table fragments across pages
        - Combine them into single, complete markdown tables
        - Preserve all rows, columns, and data
        - Remove duplicate headers that appear on continuation pages

        3. **Combining Image Descriptions**:
        - Merge related image descriptions that were separated by page breaks
        - Create complete, unified descriptions
        - Maintain all details from individual page descriptions

        4. **Preserving Content Integrity**:
        - Keep ALL existing content unchanged except for merging split elements
        - Do NOT paraphrase, summarize, or rewrite existing text
        - Do NOT add new information not present in the extracted pages
        - Do NOT remove any existing content
        - Maintain original formatting, structure, and style

        5. **Using Reference Text**:
        - Use reference text ONLY to understand context and identify split points
        - Use it to fill MINIMAL missing connector words/phrases if absolutely necessary
        - Do NOT copy large sections from reference text
        - Prioritize the extracted page content over reference text

        **OUTPUT REQUIREMENTS:**
        - Produce a single, clean document. Please maintain the structure of EXTRACTED CONTENT
        - Ensure smooth transitions between merged sections
        - Maintain all original headings, subheadings, and structure, footer, graphical details, page, footer, header, references, links etc all as it is.
        - Keep all type of data, numbers, graphical description, footer, logo, header, references, and link and specific details etc intact
        - DO NOT add any preamble or explanation - output ONLY the reconstructed document

        **CRITICAL**: Your output should be the final, complete document starting immediately with the content.."""


        rendered_prompt = PromptTemplate(template=stiching_template, input_variables=['reference_text','page_contents'], validate_template=True)


        # Format page contents with clear page markers
        formatted_pages = ""
        for i, page_content in enumerate(page_contents_list, 1):
            formatted_pages += f"\n{'='*80}\n"
            formatted_pages += f"PAGE {i}\n"
            formatted_pages += f"{'='*80}\n"
            formatted_pages += page_content
            formatted_pages += f"\n{'='*80}\n\n"
        
        # Create the complete prompt
        prompt = rendered_prompt.invoke({'reference_text':reference_text, 'page_contents':formatted_pages})
        
        
        # Call the LLM
        structured_llm = self.llm_multimodal.with_structured_output(complete_doc)
        
        response = structured_llm.invoke(prompt)
        
        return response.complete_doc
