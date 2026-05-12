# AGENTS.md

이 파일은 Codex/에이전트가 이 저장소에서 작업할 때 따라야 할 프로젝트별 지침입니다. 앞으로 이 프로젝트의 변경 작업에서는 이 문서를 우선 컨텍스트로 삼고, 코드 변경이 제품 동작을 바꾸면 관련 문서도 함께 갱신하세요.

## 프로젝트 개요

DB ERD Desktop은 Python 3.14+와 PySide6/QML 기반 Windows 데스크톱 앱입니다. MySQL, PostgreSQL, Microsoft SQL Server, Oracle에 연결해 데이터베이스/스키마 아래의 테이블과 뷰를 확인하고, 선택한 테이블로 논리/물리 ERD를 생성한 뒤 DOCX, HWPX, PPTX로 내보냅니다.

핵심 제품 요구사항은 `doc/PRD.md`에 있고, 사용자용 실행/빌드 안내는 `README.md`에 있습니다.

## 실행 및 빌드

- 개발 실행: `python run.py`
- 현재 로컬 Python 기준: `.python\3.14.5\python.exe`
- 가상환경 권장 경로: `.venv\Scripts\python.exe`
- 가상환경 생성: `.python\3.14.5\python.exe -m venv .venv`
- 기본 의존성 설치: `python -m pip install -r requirements.txt`
- EXE 패키징 의존성 포함 설치 및 빌드: `.\build_exe.ps1`
- 빌드 결과: `dist\DBErdDesktop.exe`

패키징은 `DBErdDesktop.spec`의 PyInstaller 설정을 사용합니다. DB 드라이버나 런타임 의존성이 추가되면 `pyproject.toml`, `requirements.txt`, `requirements-exe.txt`, `DBErdDesktop.spec`를 함께 검토하세요.

## 검증 기준

이 저장소에는 아직 전용 테스트 스위트가 없습니다. 변경 후 최소한 다음을 수행하세요.

- 문법/임포트 확인: `python -m compileall run.py db_erd_desktop`
- PySide6가 기본 `python`에 없으면 `.venv\Scripts\python.exe -m compileall run.py db_erd_desktop`를 사용하세요.
- 싱글 인스턴스, Qt 네트워크, UI 다이얼로그처럼 Qt 런타임이 필요한 검증은 `.venv`의 Python을 우선 사용하세요.
- DB 연결 기능 변경은 실제 DB가 없을 수 있으므로 URL 생성, 드라이버 확인, 예외 메시지, DBMS별 분기 로직을 코드 레벨로 점검하고 가능한 범위의 경량 검증을 남기세요.

## 코드 구조

- `run.py`: 앱 진입점. `db_erd_desktop.app:main`을 호출합니다.
- `db_erd_desktop/app.py`: `QApplication`, `QQmlApplicationEngine`, 싱글 인스턴스 가드, QML 루트 로딩을 담당합니다.
- `db_erd_desktop/backend.py`: QML에 노출되는 `QObject` 백엔드입니다. 세션, 연결, 트리 로딩, ERD 생성, 문서 저장 로직을 담당합니다.
- `db_erd_desktop/qml/Main.qml`: 화면, 메뉴, 모달, 연결정보 편집 다이얼로그, ERD 이미지 프리뷰를 담당합니다.
- `db_erd_desktop/single_instance.py`: `QLocalServer`/`QLocalSocket` 기반 중복 실행 방지와 기존 창 활성화 신호를 담당합니다.
- `db_erd_desktop/session_store.py`: `%APPDATA%\DBErdDesktop` 아래 Fernet 암호화 세션 파일과 키 파일을 관리합니다.
- `db_erd_desktop/models.py`: 연결 설정, 세션, 컬럼/테이블/관계/DB 모델 dataclass 정의입니다.
- `db_erd_desktop/db.py`: SQLAlchemy 엔진 생성, DBMS별 URL 구성, 네임스페이스/테이블/뷰 조회, 메타데이터 반영을 담당합니다.
- `db_erd_desktop/tunnel.py`: `sshtunnel`을 통한 SSH 포워딩을 열고 닫습니다.
- `db_erd_desktop/erd_scene.py`: `QGraphicsScene` 기반 논리/물리 ERD 렌더링과 PNG 내보내기를 담당합니다.
- `db_erd_desktop/documents.py`: DOCX/PPTX/HWPX 산출물 생성을 담당합니다.
- `db_erd_desktop/naming.py`: 물리명과 comment 기반 한글 논리명 추론 규칙입니다.

## 제품 흐름

1. 앱은 싱글 인스턴스로 실행됩니다. 이미 실행 중이면 새 프로세스는 기존 인스턴스에 활성화 요청을 보내고 종료합니다.
2. 시작 시 사용자는 저장된 세션을 열거나 새 세션을 생성해야 합니다. 작업 중 새 세션은 `Session > Create Session`으로 생성합니다.
3. 메인 화면에는 SSH/DB 입력 폼을 상시 노출하지 않습니다. 연결정보 편집은 QML의 `Session > Edit Connection Settings...` 또는 `Edit Connection Settings...` 버튼으로 엽니다.
4. 연결정보 저장은 `Session > Save Current Session`으로 수행합니다.
5. `Connect using current session`이 SSH 터널과 DB 연결을 수행하고, 연결 성공 후 트리를 로드합니다.
6. 선택된 테이블로 논리/물리 ERD를 생성한 뒤 `File > Save...` 또는 `Save...` 버튼으로 DOCX/HWPX/PPTX를 저장합니다.

## 구현 규칙

- UI/UX는 QML에 두고, 세션/DB/ERD/문서 생성 로직은 `backend.py`와 도메인 모듈에 둡니다.
- QML은 Python 객체의 프로퍼티와 슬롯을 호출하는 역할에 집중하고, DB 연결/문서 생성 같은 비즈니스 로직을 QML에 넣지 마세요.
- 장기 보관되는 데이터 구조는 `models.py` dataclass를 먼저 검토하고, 세션 직렬화 영향이 있으면 `session_store.py`의 버전/호환성을 함께 고려하세요.
- DBMS별 동작은 `db.py`에 모으고, 드라이버 누락 시 사용자가 이해할 수 있는 한국어 오류 메시지를 유지하세요.
- SSH 터널 생명주기는 `SshTunnel.close()`와 `AppBackend._close_connections()` 경로를 통해 정리되도록 하세요.
- ERD 렌더링 변경은 논리/물리 모드가 모두 정상 표시되는지 확인하고, PNG 내보내기 동작도 함께 고려하세요.
- 문서 출력 변경은 DOCX, PPTX, HWPX 세 형식의 차이를 확인하세요. 현재 HWPX는 이미지 임베딩 대신 PNG 파일명을 본문에 기록합니다.
- 비밀번호, SSH key passphrase, DB password는 로그/오류 메시지/문서에 노출하지 마세요.
- 파일 경로와 Windows 실행 흐름을 우선 고려하세요. 이 프로젝트의 주요 배포 대상은 Windows 단일 EXE입니다.
- Python 런타임은 프로젝트 로컬 `.python/`에 둘 수 있지만 저장소에는 커밋하지 않습니다. `.venv/`, `.python/`, `.uv-cache/`는 생성물로 취급하세요.

## 문서 업데이트 규칙

제품 기능, 사용자 흐름, 보안, 패키징, 산출물 형식이 바뀌면 다음을 함께 업데이트하세요.

- `doc/PRD.md`: 요구사항, 수용 기준, 향후 개선 후보
- `README.md`: 설치, 실행, 빌드, 기능, 사용자 흐름
- `AGENTS.md`: 개발자가 다음 작업에서 알아야 할 구조나 검증 절차

## 스타일

- Python 코드는 타입 힌트와 `from __future__ import annotations` 패턴을 유지하세요.
- 사용자 메시지와 오류 메시지는 현재처럼 한국어와 명확한 행동 안내를 우선합니다.
- 코드 주석은 복잡한 Qt/DB/문서 포맷 처리처럼 의도가 바로 드러나지 않는 곳에만 짧게 추가하세요.
- 불필요한 대규모 리팩터링은 피하고, 기능 단위로 작게 변경하세요.
