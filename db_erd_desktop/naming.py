from __future__ import annotations

import re


TOKEN_MAP = {
    "account": "계정",
    "addr": "주소",
    "address": "주소",
    "amount": "금액",
    "auth": "인증",
    "birth": "생년월일",
    "board": "게시판",
    "category": "카테고리",
    "cd": "코드",
    "city": "도시",
    "code": "코드",
    "comment": "댓글",
    "company": "회사",
    "content": "내용",
    "count": "건수",
    "country": "국가",
    "created": "생성",
    "customer": "고객",
    "date": "일자",
    "deleted": "삭제",
    "dept": "부서",
    "department": "부서",
    "desc": "설명",
    "description": "설명",
    "email": "이메일",
    "employee": "직원",
    "end": "종료",
    "dtl": "상세",
    "file": "파일",
    "flag": "여부",
    "gender": "성별",
    "group": "그룹",
    "history": "이력",
    "id": "식별자",
    "image": "이미지",
    "invoice": "청구",
    "is": "여부",
    "item": "항목",
    "log": "로그",
    "manager": "관리자",
    "member": "회원",
    "memo": "메모",
    "name": "이름",
    "no": "번호",
    "number": "번호",
    "order": "주문",
    "password": "비밀번호",
    "payment": "결제",
    "permission": "권한",
    "phone": "전화번호",
    "post": "게시글",
    "price": "가격",
    "product": "상품",
    "qty": "수량",
    "quantity": "수량",
    "role": "역할",
    "session": "세션",
    "start": "시작",
    "state": "상태",
    "status": "상태",
    "title": "제목",
    "token": "토큰",
    "type": "유형",
    "updated": "수정",
    "use": "사용",
    "user": "사용자",
    "yn": "여부",
    "zip": "우편번호",
}

COMMON_PHRASES = {
    ("created", "at"): "생성 일시",
    ("updated", "at"): "수정 일시",
    ("deleted", "at"): "삭제 일시",
    ("created", "date"): "생성 일자",
    ("updated", "date"): "수정 일자",
    ("start", "date"): "시작 일자",
    ("end", "date"): "종료 일자",
    ("user", "id"): "사용자 식별자",
    ("member", "id"): "회원 식별자",
    ("customer", "id"): "고객 식별자",
    ("order", "id"): "주문 식별자",
    ("order", "no"): "주문 번호",
    ("product", "id"): "상품 식별자",
    ("phone", "no"): "전화번호",
    ("zip", "code"): "우편번호",
}

IGNORED_PREFIXES = {"t", "tb", "tbl", "mst", "m", "dtl", "d"}


def infer_logical_name(comment: str | None, physical_name: str) -> str:
    comment_line = _first_line(comment)
    if comment_line and _has_hangul(comment_line):
        return comment_line

    tokens = _tokens(physical_name)
    phrase = _phrase(tokens)
    if phrase:
        return phrase

    translated = [TOKEN_MAP.get(token, token.title()) for token in tokens]
    value = " ".join(translated).strip()
    if value:
        return value
    if comment_line:
        return comment_line
    return physical_name


def _tokens(name: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    raw = re.split(r"[^0-9A-Za-z가-힣]+", spaced.lower())
    tokens = [_singular(token) for token in raw if token]
    while tokens and tokens[0] in IGNORED_PREFIXES:
        tokens.pop(0)
    return tokens


def _phrase(tokens: list[str]) -> str | None:
    if tuple(tokens) in COMMON_PHRASES:
        return COMMON_PHRASES[tuple(tokens)]
    if len(tokens) >= 2 and tuple(tokens[-2:]) in COMMON_PHRASES:
        head = [TOKEN_MAP.get(token, token.title()) for token in tokens[:-2]]
        return " ".join([*head, COMMON_PHRASES[tuple(tokens[-2:])]]).strip()
    return None


def _singular(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("s") and len(token) > 3 and token not in {"status"}:
        return token[:-1]
    return token


def _first_line(value: str | None) -> str | None:
    if not value:
        return None
    line = value.strip().splitlines()[0].strip()
    return line or None


def _has_hangul(value: str) -> bool:
    return any("가" <= char <= "힣" for char in value)
