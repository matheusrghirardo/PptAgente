"""Generator module: converts slide data into a .pptx file."""

from pptx import Presentation
from pptx.util import Inches, Pt


def create_presentation(slides: list[dict], output_path: str = "presentation.pptx") -> str:
    """Build a PowerPoint file from *slides* and save it to *output_path*.

    Each element of *slides* must be a dict with:
        - title   (str)
        - bullets (list[str])

    Returns the resolved output path.
    """
    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    title_slide_layout = prs.slide_layouts[0]   # Title Slide
    content_layout = prs.slide_layouts[1]        # Title and Content

    for index, slide_data in enumerate(slides):
        layout = title_slide_layout if index == 0 else content_layout
        slide = prs.slides.add_slide(layout)

        # Set title
        title_shape = slide.shapes.title
        title_shape.text = slide_data.get("title", "")

        # Set body / bullets
        bullets = slide_data.get("bullets", [])
        if bullets:
            # Layout 0 has a subtitle placeholder; layout 1 has a content placeholder
            body_placeholder = slide.placeholders[1]
            tf = body_placeholder.text_frame
            tf.clear()

            for i, bullet in enumerate(bullets):
                if i == 0:
                    paragraph = tf.paragraphs[0]
                else:
                    paragraph = tf.add_paragraph()
                paragraph.text = bullet
                paragraph.level = 0
                if paragraph.runs:
                    paragraph.runs[0].font.size = Pt(20)

    prs.save(output_path)
    return output_path
