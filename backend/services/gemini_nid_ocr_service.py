import json
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, field_validator

from config import get_settings


class NIDOcrExtractionResult(BaseModel):
    document_detected: bool = False
    name: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    nid_number: Optional[str] = None
    image_quality: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)

    @field_validator("warnings", mode="before")
    @classmethod
    def _normalize_warnings(cls, value):
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        return [str(value)]


class NIDOcrExtractionError(RuntimeError):
    pass


class GeminiNidOcrService:
    REQUEST_TIMEOUT_SECONDS = 30

    def __init__(self) -> None:
        settings = get_settings()
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is required to start the NID OCR extraction service"
            )

        self._client = genai.Client(api_key=api_key)
        self._logger = logging.getLogger(__name__)

    def extract(self, image_data: bytes, content_type: str) -> NIDOcrExtractionResult:
        prompt = (
            "You are extracting text from the FRONT side of a Bangladesh National ID card.\n"
            "Return only structured JSON.\n"
            "Do not guess unreadable values. If a field is unclear, use null.\n"
            "If the image is not a Bangladesh NID front side, set document_detected to false.\n"
            "For date_of_birth, use YYYY-MM-DD when readable, otherwise null.\n"
            "For warnings, return a list of short strings describing any uncertainty or quality issues.\n"
            "The image_quality value should be one of: excellent, good, fair, poor, unreadable.\n"
        )

        schema = types.Schema(
            type=types.Type.OBJECT,
            required=["document_detected", "warnings"],
            properties={
                "document_detected": types.Schema(type=types.Type.BOOLEAN),
                "name": types.Schema(type=types.Type.STRING),
                "father_name": types.Schema(type=types.Type.STRING),
                "mother_name": types.Schema(type=types.Type.STRING),
                "date_of_birth": types.Schema(type=types.Type.STRING),
                "nid_number": types.Schema(type=types.Type.STRING),
                "image_quality": types.Schema(type=types.Type.STRING),
                "warnings": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(type=types.Type.STRING),
                ),
            },
        )

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    self._client.models.generate_content,
                    model="gemini-2.5-flash",
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_text(text=prompt),
                                types.Part.from_bytes(
                                    data=image_data,
                                    mime_type=content_type,
                                ),
                            ],
                        )
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0,
                        response_mime_type="application/json",
                        response_schema=schema,
                    ),
                )
                response = future.result(timeout=self.REQUEST_TIMEOUT_SECONDS)

            raw_text = (response.text or "").strip()
            if not raw_text:
                raise NIDOcrExtractionError("Gemini returned an empty OCR response")

            try:
                payload = json.loads(raw_text)
            except json.JSONDecodeError as exc:
                raise NIDOcrExtractionError("Gemini OCR response was not valid JSON") from exc

            if not isinstance(payload, dict):
                raise NIDOcrExtractionError("Gemini OCR response was not an object")

            try:
                return NIDOcrExtractionResult.model_validate(payload)
            except Exception as exc:
                raise NIDOcrExtractionError("Gemini OCR response did not match the expected schema") from exc
        except NIDOcrExtractionError:
            raise
        except FuturesTimeoutError as exc:
            raise NIDOcrExtractionError(
                "Gemini OCR request timed out"
            ) from exc
        except Exception as exc:
            self._logger.exception("Gemini OCR request failed")
            raise NIDOcrExtractionError(
                f"Gemini OCR request failed: {type(exc).__name__}"
            ) from exc


ocr_service = GeminiNidOcrService()
