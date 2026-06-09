"""PDF 文本提取接口"""
from fastapi import APIRouter, UploadFile, File, HTTPException
import io

router = APIRouter(prefix="/api", tags=["PDF"])

@router.post("/extract-pdf")
async def extract_pdf_text(file: UploadFile = File(...)):
    """提取 PDF 文件中的文本"""
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(400, "请上传 PDF 文件")

    try:
        import pdfplumber
        contents = await file.read()
        text_parts = []
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            for page in pdf.pages[:10]:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        text = "\n".join(text_parts)[:5000]
        if not text.strip():
            raise HTTPException(400, "PDF 中未检测到文字，可能是扫描版或图片格式")
        return {"text": text, "length": len(text)}
    except Exception as e:
        raise HTTPException(500, f"PDF 解析失败: {str(e)[:100]}")
