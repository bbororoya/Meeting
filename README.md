# 📍 미팅 동선 공유 지도

여러 사람이 같은 링크에서 미팅 정보를 입력하면, 새로고침 시 지도에 위치와 동선이 갱신되는 Streamlit 앱입니다.

- **저장**: 구글 시트 (모두가 같은 시트에 기록 → 자동 공유)
- **지오코딩**: 카카오 로컬 API (국내 주소 → 좌표)
- **지도**: folium (마커 + 미팅 정보 팝업 + 동선)

---

## 준비물 2가지

### 1. 카카오 REST API 키 (무료)
1. https://developers.kakao.com 접속 → 로그인
2. **내 애플리케이션 → 애플리케이션 추가**
3. 생성된 앱의 **앱 키 → REST API 키** 복사
4. (지오코딩만 쓰면 별도 도메인 등록 없이 동작합니다)

### 2. 구글 시트 + 서비스 계정 (무료)
1. https://console.cloud.google.com 에서 프로젝트 생성
2. **API 및 서비스 → 라이브러리** 에서 `Google Sheets API` 와 `Google Drive API` **사용 설정**
3. **사용자 인증 정보 → 사용자 인증 정보 만들기 → 서비스 계정** 생성
4. 만든 서비스 계정 → **키 → 키 추가 → JSON** 다운로드 (이 파일 내용이 secrets에 들어갑니다)
5. 구글 시트를 새로 하나 만들고, JSON 안의 `client_email` 주소를 그 시트에 **편집자로 공유**
6. 시트 URL에서 `/d/` 와 `/edit` 사이의 문자열이 **sheet_id** 입니다
   예) `https://docs.google.com/spreadsheets/d/`**`1AbC...xyz`**`/edit`

---

## secrets 설정

`.streamlit/secrets.toml` 파일을 만들고 아래처럼 채웁니다.
(`secrets.toml.example` 을 복사해서 쓰면 됩니다.)

```toml
kakao_rest_api_key = "여기에_카카오_REST_API_키"
sheet_id = "여기에_구글시트_ID"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@...iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

> `[gcp_service_account]` 아래 값들은 다운로드한 JSON 파일의 내용을 그대로 옮기면 됩니다.
> `private_key` 의 줄바꿈은 `\n` 형태 그대로 두세요.

---

## 실행

### 로컬에서
```bash
pip install -r requirements.txt
streamlit run app.py
```
브라우저에서 http://localhost:8501 로 열립니다.

### 다른 사람과 공유 (Streamlit Cloud, 무료)
1. 이 폴더를 GitHub 저장소에 올립니다 (단, `secrets.toml` 은 올리지 마세요)
2. https://share.streamlit.io 에서 저장소를 연결해 배포
3. Streamlit Cloud의 **Settings → Secrets** 에 위 `secrets.toml` 내용을 그대로 붙여넣기
4. 생성된 링크를 팀원에게 공유하면, 누구나 입력하고 새로고침하면 갱신됩니다

---

## 동작 방식
- 입력 폼 제출 → 카카오 API가 주소를 좌표로 변환 → 구글 시트에 한 줄 추가
- 지도는 시트를 읽어 **일시 순서대로** 마커를 찍고 점선으로 동선을 연결
- 마커를 클릭하면 미팅명·시간·참석자·메모·작성자가 팝업으로 표시
- "🔄 새로고침" 버튼 또는 브라우저 새로고침으로 최신 상태 반영

## 자주 묻는 것
- **주소를 못 찾는다고 나와요** → 도로명/지번 주소를 더 정확히 입력해 보세요. 건물명만으로는 실패할 수 있습니다.
- **입력했는데 지도에 안 보여요** → 새로고침을 눌러 주세요. (이 버전은 "새로고침 시 갱신" 방식입니다)
- **순서를 바꾸고 싶어요** → 동선은 '일시' 기준으로 정렬됩니다. 시간을 조정하면 순서가 바뀝니다.
