import io
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import HTTPException
from PIL import Image

from app.schemas.resumeio import Extension


@dataclass
class ResumeioDownloader:
    """
    Class to download a resume from resume.io and convert it to a PDF.

    Parameters
    ----------
    rendering_token : str
        Rendering Token of the resume to download.
    extension : Extension, optional
        Image extension to download, by default "jpeg".
    image_size : int, optional
        Size of the images to download, by default 2000.
    """

    rendering_token: str
    extension: Extension = Extension.jpeg
    image_size: int = 2000
    IMAGE_URL: str = (
        "https://ssr.resume.tools/to-image/{rendering_token}-{page}.{extension}?cache={cache_date}&size={image_size}"
    )

    def __post_init__(self) -> None:
        """Set the cache date to the current time."""
        self.cache_date = datetime.now(timezone.utc).isoformat()[:-10] + "Z"

    @staticmethod
    def _is_blank_image(img: Image.Image) -> bool:
        """Check if an image is a blank placeholder by sampling pixels.

        resume.tools returns a near-white PNG placeholder for invalid
        tokens or non-existent pages. Real resume pages have text,
        colors, and graphical elements that make the average pixel
        color significantly different from pure white.

        Parameters
        ----------
        img : Image.Image
            The image to check.

        Returns
        -------
        bool
            True if the image appears to be a blank placeholder.
        """
        # A blank placeholder from resume.io only has very faint colors (the watermark).
        # Its darkest pixel is around RGB(221, 227, 240).
        # A real resume page will have text or graphics, meaning it will have 
        # much darker pixels (well below 150).
        extrema = img.convert("RGB").getextrema()
        min_r, min_g, min_b = extrema[0][0], extrema[1][0], extrema[2][0]
        
        # If the darkest pixel in the entire image is still very light, it's the blank placeholder.
        if min_r > 150 and min_g > 150 and min_b > 150:
            return True
            
        return False

    def generate_pdf(self) -> bytes:
        """
        Generate a PDF from the resume.io resume (supports multi-page).

        Downloads pages sequentially until a blank placeholder is detected.
        Merges all valid pages into a single PDF.

        Returns
        -------
        bytes
            PDF representation of the resume.

        Raises
        ------
        HTTPException
            If no valid resume pages could be downloaded.
        """
        images = self._download_all_pages()

        if not images:
            raise HTTPException(
                status_code=404,
                detail=f"No valid resume found for this rendering token. "
                "Please check your token and try again.",
            )

        first_page = images[0]
        additional_pages = images[1:] if len(images) > 1 else []

        pdf_buffer = io.BytesIO()
        if additional_pages:
            first_page.save(
                pdf_buffer,
                format="PDF",
                resolution=300.0,
                save_all=True,
                append_images=additional_pages,
            )
        else:
            first_page.save(pdf_buffer, format="PDF", resolution=300.0)

        return pdf_buffer.getvalue()

    def _download_all_pages(self) -> list[Image.Image]:
        """Download all valid (non-blank) pages of the resume.

        Returns
        -------
        list[Image.Image]
            List of PIL Image objects for each valid page.
        """
        images = []
        for page in range(1, 11):  # Max 10 pages safety limit
            page_img = self._try_download_page(page)
            if page_img is None:
                break
            images.append(page_img)
        return images

    def _try_download_page(self, page: int) -> Optional[Image.Image]:
        """Try to download a single page of the resume.

        Returns None if the page is a blank placeholder or an error occurs.

        Parameters
        ----------
        page : int
            Page number to download (1-indexed).

        Returns
        -------
        Optional[Image.Image]
            PIL Image in RGB mode, or None if page is blank/invalid.
        """
        image_url = self.IMAGE_URL.format(
            rendering_token=self.rendering_token,
            page=page,
            extension=self.extension.value,
            cache_date=self.cache_date,
            image_size=self.image_size,
        )
        try:
            response = requests.get(
                image_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/136.0.0.0 Safari/537.36",
                },
                timeout=30,
            )
        except requests.RequestException:
            return None

        if response.status_code != 200:
            return None

        # Verify content is an image
        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            return None

        try:
            img = Image.open(io.BytesIO(response.content))

            # Detect blank placeholder images
            if self._is_blank_image(img):
                return None

            # Convert to RGB for PDF compatibility
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            return img
        except Exception:
            return None
