import os
import pymupdf


def convert_pdf_to_images(pdf_path: str, tmpdir: str):
    """Convert PDF pages to images using configuration settings."""
    pdf_doc = None
    try:
        # Open PDF with error checking
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        pdf_doc = pymupdf.open(pdf_path)
        if pdf_doc.is_closed:
            raise Exception("PDF document is closed after opening")

        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        pages_count = len(pdf_doc)
        print(f"Converting {pdf_name} with {pages_count} pages.")

        if pages_count == 0:
            raise Exception("PDF contains no pages")

        # Create a directory to store image files
        image_output_dir = os.path.join(tmpdir, pdf_name)
        os.makedirs(image_output_dir, exist_ok=True)

        image_format = "png"
        dpi = 300

        for i in range(pages_count):
            try:
                page = pdf_doc[i]
                # Use a reasonable DPI to avoid memory issues
                pixmap = page.get_pixmap(dpi=dpi)
                extension = (
                    "jpg" if image_format.upper() == "JPEG" else image_format.lower()
                )
                img_path = os.path.join(image_output_dir, f"page_{i + 1}.{extension}")
                pixmap.save(img_path, image_format)

                # Clear pixmap to free memory
                pixmap = None

                if i % 10 == 0:  # Log progress every 10 pages
                    print(f"Processed page {i + 1}/{pages_count}")

            except Exception as e:
                print(f"Error processing page {i + 1}: {str(e)}")
                raise

        print(
            f"Saved {pages_count} images for {pdf_name} at {dpi} DPI in {image_format} format."
        )
        return pages_count, image_output_dir

    except Exception as e:
        print(f"Error converting PDF to images: {str(e)}")
        raise
    finally:
        # Ensure PDF is properly closed
        if pdf_doc and not pdf_doc.is_closed:
            pdf_doc.close()
