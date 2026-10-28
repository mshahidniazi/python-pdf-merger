
from pathlib import Path
import logging
import os
import tempfile

from pypdf import PdfReader, PdfWriter


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

# Safety limits — adjust for your application
MAX_FILES = 100
MAX_TOTAL_SIZE_MB = 500


def merge_pdfs(pdf_list, output_path):
    """Merge multiple PDF files into one PDF safely."""

    if not isinstance(pdf_list, (list, tuple)) or len(pdf_list) < 2:
        raise ValueError("Provide at least two PDF files.")

    if len(pdf_list) > MAX_FILES:
        raise ValueError(f"Maximum allowed files: {MAX_FILES}.")

    output = Path(output_path).expanduser().resolve()
    temp_path = None
    writer = PdfWriter()

    try:
        # Validate output path
        if output.suffix.lower() != ".pdf":
            raise ValueError("Output filename must end with .pdf.")

        if not output.parent.is_dir():
            raise ValueError("Output directory does not exist.")

        # Validate input paths and prevent overwriting inputs
        inputs = [Path(p).expanduser().resolve() for p in pdf_list]

        if len(set(inputs)) != len(inputs):
            raise ValueError("Duplicate input file paths are not allowed.")

        if output in inputs:
            raise ValueError("Output file cannot also be an input file.")

        total_size = 0

        for path in inputs:
            if not path.is_file():
                raise FileNotFoundError(f"File not found: {path}")

            if path.suffix.lower() != ".pdf":
                raise ValueError(f"Not a PDF file: {path.name}")

            if not os.access(path, os.R_OK):
                raise PermissionError(f"Cannot read: {path}")

            total_size += path.stat().st_size

        if total_size > MAX_TOTAL_SIZE_MB * 1024 * 1024:
            raise ValueError(
                f"Total input size exceeds {MAX_TOTAL_SIZE_MB} MB."
            )

        # Validate PDFs before merging
        for path in inputs:
            with path.open("rb") as pdf_file:
                reader = PdfReader(pdf_file, strict=True)

                if reader.is_encrypted:
                    raise ValueError(
                        f"Password-protected PDF is not supported: "
                        f"{path.name}"
                    )

                if len(reader.pages) == 0:
                    raise ValueError(f"PDF contains no pages: {path.name}")

        # Append PDFs in the provided order
        for path in inputs:
            writer.append(str(path))

        # Write to a temporary file first
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".pdf",
            prefix=".merge_",
            dir=output.parent,
            delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            writer.write(temp_file)

        writer.close()
        writer = None

        # Verify the generated PDF
        with temp_path.open("rb") as pdf_file:
            merged_reader = PdfReader(pdf_file, strict=True)

            if merged_reader.is_encrypted or len(merged_reader.pages) == 0:
                raise ValueError("Generated PDF failed verification.")

            page_count = len(merged_reader.pages)

        # Replace destination only after successful verification
        os.replace(temp_path, output)
        temp_path = None

        logger.info(
            "Successfully merged %d files into %s (%d pages).",
            len(inputs),
            output,
            page_count
        )

        return output

    except Exception:
        logger.exception("PDF merging failed.")
        raise

    finally:
        if writer is not None:
            writer.close()

        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                logger.exception("Could not remove temporary file.")


if __name__ == "__main__":
    files = [
        "sample1.pdf",
        "sample2.pdf"
    ]

    try:
        result = merge_pdfs(files, "merged_output.pdf")
        print(f"PDF merger completed: {result}")

    except (ValueError, OSError, Exception) as error:
        print(f"Error: {error}")
