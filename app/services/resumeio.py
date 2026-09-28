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
    rendering_token: str
    extension: Extension = Extension.jpeg
    image_size: int = 2000
    IMAGE_URL: str = (
        "https://ssr.resume.tools/to-image/{rendering_token}-{page}.{extension}?cache={cache_date}&size={image_size}"
    )

    def __post_init__(self) -> None:
        self.cache_date = datetime.now(timezone.utc).isoformat()[:-10] + "Z"

    def generate_pdf(self) -> bytes:
        first_page_bytes = self.__download_image(page=1)
        img = Image.open(first_page_bytes)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        images = []
        for page in range(2, 11):
            page_bytes = self.__try_download_page(page)
            if not page_bytes:
                break
            page_img = Image.open(page_bytes)
            if page_img.mode in ("RGBA", "P"):
                page_img = page_img.convert("RGB")
            images.append(page_img)

        pdf_buffer = io.BytesIO()
        if images:
            img.save(pdf_buffer, format="PDF", resolution=300.0, save_all=True, append_images=images)
        else:
            img.save(pdf_buffer, format="PDF", resolution=300.0)
        return pdf_buffer.getvalue()

    def __download_image(self, page: int = 1) -> io.BytesIO:
        image_url = self.IMAGE_URL.format(
            rendering_token=self.rendering_token,
            page=page,
            extension=self.extension.value,
            cache_date=self.cache_date,
            image_size=self.image_size,
        )
        response = self.__get(image_url)
        return io.BytesIO(response.content)

    def __try_download_page(self, page: int) -> Optional[io.BytesIO]:
        image_url = self.IMAGE_URL.format(
            rendering_token=self.rendering_token,
            page=page,
            extension=self.extension.value,
            cache_date=self.cache_date,
            image_size=self.image_size,
        )
        response = requests.get(
            image_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36",
            },
        )
        if response.status_code == 200:
            return io.BytesIO(response.content)
        return None

    def __get(self, url: str) -> requests.Response:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36",
            },
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Unable to download resume (rendering token: {self.rendering_token})",
            )
        return response
