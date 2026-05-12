# DB ERD Desktop

Python Qt6/QML 데스크톱 앱입니다. MySQL, PostgreSQL, Microsoft SQL Server, Oracle에 연결해 데이터베이스/스키마 아래의 테이블과 뷰를 계층적으로 확인하고, 선택한 테이블로 논리/물리 ERD를 그린 뒤 DOCX, HWPX, PPTX로 문서화합니다.

## 설치

Python 3.14 이상이 필요합니다. 현재 개발 환경의 `.venv`는 Python 3.14.5 기준으로 구성되어 있습니다. `.python\3.14.5\python.exe`가 없는 환경에서는 Python 3.14.5 이상을 설치한 뒤 해당 `python.exe`로 가상환경을 만드세요.

```powershell
.\.python\3.14.5\python.exe -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
```

사용할 DBMS 드라이버도 추가로 설치하세요.

```powershell
# 예시: 모두 설치
python -m pip install "PyMySQL>=1.1.3" "psycopg[binary]>=3.3.4" "pyodbc>=5.3.0" "oracledb>=4.0.0"
```

MSSQL은 로컬에 Microsoft ODBC Driver 17/18 for SQL Server가 설치되어 있어야 합니다.

## 실행

```powershell
python run.py
```

앱은 싱글 인스턴스로 동작합니다. 이미 실행 중인 상태에서 다시 실행하면 새 창을 만들지 않고 기존 창 또는 현재 열린 모달 창을 앞으로 가져온 뒤 두 번째 프로세스는 종료됩니다.

## EXE 빌드

```powershell
.\build_exe.ps1
```

빌드 결과:

```text
dist\DBErdDesktop.exe
```

## 기능

- 싱글 인스턴스 실행: 중복 실행 시 기존 실행 창을 활성화하고 새 인스턴스는 종료
- QML UI 분리: 화면/모달/메뉴는 `db_erd_desktop/qml/Main.qml`, 세션/DB/ERD/문서 로직은 Python 백엔드에서 처리
- 세션 관리: 첫 화면 모달에서 저장된 세션 열기 또는 새 세션 생성을 선택하고, 세션 생성은 별도 화면에서 진행
- 세션 생성 메뉴: `Session > Create Session`에서 새 세션 생성 모달을 열고 생성 후 연결정보 입력으로 이동
- 세션 저장: 메인 작업 화면에는 세션 설정 패널을 표시하지 않고 `Session > Save Current Session` 메뉴로 현재 연결정보 저장
- 연결정보 편집: 메인 작업 화면에는 SSH/DB 계정 입력 폼을 표시하지 않고 `Session > Edit Connection Settings...` 다이얼로그에서 편집
- 세션 암호화 저장: SSH/DB 연결정보와 계정정보를 `%APPDATA%\DBErdDesktop\sessions.enc`에 암호화 저장
- SSH 터널 연결: SSH 서버 계정/비밀번호 또는 private key 입력 후 터널 생성
- 연결 정보 입력: DBMS, 호스트, 포트, DB/서비스명, 사용자, 비밀번호
- 데이터베이스/스키마 아래에 `Tables`와 `Views` 그룹을 나눠 트리 구조로 조회하고, ERD 대상 테이블을 선택
- 논리 ERD: 테이블/컬럼 주석이 한글이면 우선 사용하고, 없으면 물리명을 한글 의미로 추론
- 물리 ERD: 컬럼 타입, PK/FK, NULL 여부, 기본값 표시
- 관계선 표시: 선택된 테이블 간 FK 관계를 ERD 연결선으로 렌더링
- 저장 메뉴: `File > Save...`에서 저장 위치와 DOCX/HWPX/PPTX 형식 선택
- 문서화: DOCX/PPTX는 ERD PNG를 문서 안에 삽입, HWPX는 텍스트 문서와 ERD PNG 파일을 함께 생성

## 세션 사용 흐름

1. 앱을 실행하면 먼저 모달 다이얼로그가 열립니다.
2. 기존 세션을 선택해 `Open Session`을 누르거나 `Create Session`으로 새 세션 생성 화면을 엽니다. 새 세션 생성 화면이 열려 있는 동안 뒤쪽 세션 선택 화면은 비활성화됩니다.
3. 별도 생성 화면에서 세션명과 설명을 입력해 암호화 세션 레코드를 만듭니다.
4. 새 세션을 만들면 연결정보 모달이 열리며, SSH/DB 연결정보를 입력한 뒤 `Session > Save Current Session`으로 같은 세션에 저장합니다.
5. 세션 파일은 암호화되어 `%APPDATA%\DBErdDesktop\sessions.enc`에 저장됩니다.
6. 세션을 불러온 뒤 `Connect using current session`을 누르면 저장된 SSH/DB 정보로 연결합니다.

작업 중 새 세션이 필요하면 `Session > Create Session`으로 같은 생성 모달을 열 수 있습니다. 이 메뉴는 현재 DB에 연결되어 있지 않을 때 사용할 수 있습니다.

## QML 구조

- `db_erd_desktop/qml/Main.qml`: 화면, 메뉴, 모달 다이얼로그, ERD 이미지 프리뷰
- `db_erd_desktop/backend.py`: QML에 노출되는 `QObject` 백엔드, 세션/DB/ERD/문서 저장 로직
- `db_erd_desktop/db.py`, `tunnel.py`, `documents.py`, `erd_scene.py`: 도메인 로직 모듈

## SSH 터널 사용 흐름

1. `Session > Edit Connection Settings...`를 엽니다.
2. `Use SSH tunnel`을 체크합니다.
3. SSH 서버 호스트, 포트, 계정, 비밀번호 또는 private key를 입력합니다.
4. DB 정보에는 SSH 서버에서 접근 가능한 DB 호스트/포트를 입력합니다. 예: DB가 SSH 서버 내부에서만 보이면 `127.0.0.1:3306`.
5. `Connect using current session`을 누르면 SSH 터널을 열고 DB에 연결한 뒤 데이터베이스/스키마, 테이블, 뷰 트리를 불러옵니다.
6. 트리에서 `Tables` 그룹 아래 필요한 테이블을 선택하고 `Generate ERD`를 누릅니다. `Views` 그룹은 구조 확인용으로 표시되며 ERD 생성 대상에는 포함되지 않습니다.
7. `File > Save...` 또는 `Save...` 버튼으로 저장 위치와 형식을 선택합니다.

## 출력물

문서 저장 시 같은 폴더에 다음 PNG도 같이 생성됩니다.

- `*_logical.png`
- `*_physical.png`

HWPX는 이미지 임베딩 대신 문서 본문에 PNG 파일명을 기록합니다. DOCX/PPTX는 PNG를 문서에 직접 포함합니다.
