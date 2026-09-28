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

    def generate_pdf(self, num_pages: int = 1) -> bytes:
        """
        Generate a PDF from the resume.io resume.

        Downloads the exact number of pages requested by the user.

        Returns
        -------
        bytes
            PDF representation of the resume.

        Raises
        ------
        HTTPException
            If no valid resume pages could be downloaded.
        """
        images = []
        for page in range(1, num_pages + 1):
            page_img = self._try_download_page(page)
            if page_img:
                images.append(page_img)

        if not images:
            raise HTTPException(
                status_code=404,
                detail="No valid resume found for this rendering token. Please check your token.",
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

    def _try_download_page(self, page: int) -> Optional[Image.Image]:
        """Try to download a single page of the resume.

        Returns None if the download fails (e.g., 403 or 404).

        Parameters
        ----------
        page : int
            Page number to download (1-indexed).

        Returns
        -------
        Optional[Image.Image]
            PIL Image in RGB mode, or None if page download failed.
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

            # Convert to RGB for PDF compatibility
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            return img
        except Exception:
            return None
