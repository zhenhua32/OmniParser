from typing import Optional

import gradio as gr
import numpy as np
import torch
from PIL import Image
import io


import base64, os
from utils import check_ocr_box, get_yolo_model, get_caption_model_processor, get_som_labeled_img
import torch
from PIL import Image

# 加载模型
yolo_model = get_yolo_model(model_path="weights/icon_detect/best.pt")
# 加载处理器
caption_model_processor = get_caption_model_processor(
    model_name="florence2", model_name_or_path="weights/icon_caption_florence"
)
platform = "pc"
if platform == "pc":
    draw_bbox_config = {
        "text_scale": 0.8,
        "text_thickness": 2,
        "text_padding": 2,
        "thickness": 2,
    }
elif platform == "web":
    draw_bbox_config = {
        "text_scale": 0.8,
        "text_thickness": 2,
        "text_padding": 3,
        "thickness": 3,
    }
elif platform == "mobile":
    draw_bbox_config = {
        "text_scale": 0.8,
        "text_thickness": 2,
        "text_padding": 3,
        "thickness": 3,
    }


MARKDOWN = """
# OmniParser for Pure Vision Based General GUI Agent 🔥
<div>
    <a href="https://arxiv.org/pdf/2408.00203">
        <img src="https://img.shields.io/badge/arXiv-2408.00203-b31b1b.svg" alt="Arxiv" style="display:inline-block;">
    </a>
</div>

OmniParser is a screen parsing tool to convert general GUI screen to structured elements. 
"""

DEVICE = torch.device("cuda")


# @spaces.GPU
# @torch.inference_mode()
# @torch.autocast(device_type="cuda", dtype=torch.bfloat16)
def process(image_input, box_threshold, iou_threshold) -> Optional[Image.Image]:
    # 保存图片
    image_save_path = "imgs/saved_image_demo.png"
    image_input.save(image_save_path)
    # import pdb; pdb.set_trace()

    # 调用函数
    ocr_bbox_rslt, is_goal_filtered = check_ocr_box(
        image_save_path,
        display_img=False,
        output_bb_format="xyxy",
        goal_filtering=None,
        easyocr_args={"paragraph": False, "text_threshold": 0.9},
    )
    # 一个文本列表, 一个是位置列表
    text, ocr_bbox = ocr_bbox_rslt
    # print('prompt:', prompt)
    dino_labled_img, label_coordinates, parsed_content_list = get_som_labeled_img(
        image_save_path,
        yolo_model,
        BOX_TRESHOLD=box_threshold,
        output_coord_in_ratio=True,
        ocr_bbox=ocr_bbox,
        draw_bbox_config=draw_bbox_config,
        caption_model_processor=caption_model_processor,
        ocr_text=text,
        iou_threshold=iou_threshold,
    )
    # dino_labled_img 是 base64 编码的图片
    image = Image.open(io.BytesIO(base64.b64decode(dino_labled_img)))  # 这个是画框的图片
    print("finish processing")
    parsed_content_list = "\n".join(parsed_content_list)  # 这个是文本输出
    return image, str(parsed_content_list)


with gr.Blocks() as demo:
    gr.Markdown(MARKDOWN)
    with gr.Row():
        with gr.Column():
            image_input_component = gr.Image(type="pil", label="Upload image")
            # set the threshold for removing the bounding boxes with low confidence, default is 0.05
            box_threshold_component = gr.Slider(label="Box Threshold", minimum=0.01, maximum=1.0, step=0.01, value=0.05)
            # set the threshold for removing the bounding boxes with large overlap, default is 0.1
            iou_threshold_component = gr.Slider(label="IOU Threshold", minimum=0.01, maximum=1.0, step=0.01, value=0.1)
            submit_button_component = gr.Button(value="Submit", variant="primary")
        with gr.Column():
            image_output_component = gr.Image(type="pil", label="Image Output")
            text_output_component = gr.Textbox(label="Parsed screen elements", placeholder="Text Output")

    submit_button_component.click(
        fn=process,
        inputs=[image_input_component, box_threshold_component, iou_threshold_component],
        outputs=[image_output_component, text_output_component],
    )

# demo.launch(debug=False, show_error=True, share=True)
demo.launch(share=True, server_port=7861, server_name="0.0.0.0")
