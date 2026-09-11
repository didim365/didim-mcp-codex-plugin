# 사내망 TLS 검사(FortiGate) CA

사내망은 FortiGate 가 TLS 를 검사한다. 컨테이너 안에는 그 CA 가 없어서 `npm ci` 와
`uv sync` 가 `SELF_SIGNED_CERT_IN_CHAIN` 으로 죽는다(호스트에는 CA 가 깔려 있어 로컬
빌드는 멀쩡하므로 **컨테이너에서만** 드러난다).

이 디렉터리의 `*.crt` 는 Docker build 단계에서 컨테이너 신뢰 저장소에 들어간다.

## 이 저장소에는 `.crt` 가 없다

**이 저장소는 public 이다.** CA 공개 인증서에 비밀값은 없지만, 사내 TLS 검사 장비의
존재와 일련번호(인증서 CN)를 인터넷에 공개할 이유가 없다. 그래서 `certs/*.crt` 는
`.gitignore` 에 있고 빌드하는 쪽이 직접 넣는다.

- **로컬 빌드**: 사내 다른 저장소에서 같은 파일을 복사한다.
  ```bash
  cp ../didim-rag-backend/certs/fortigate-ca.crt certs/
  ```
- **Jenkins**: `didim-fortigate-ca` (Secret file) 자격증명이 `Prepare CA` stage 에서
  이 디렉터리에 놓는다. 자격증명이 없으면 stage 가 건너뛰고, 사내망에서는 `npm ci`
  단계에서 실패한다.

`.crt` 가 없어도 Dockerfile 은 그대로 돈다(빈 bundle 로 진행). 사외망·CI 격리 환경에서
빌드할 때는 파일이 필요 없다.

## 규칙

- **private key 를 이 디렉터리에 두지 않는다.** 여기 들어가는 것은 CA 공개 인증서뿐이다.
- 클라이언트 인증서·운영 서버 인증서도 두지 않는다. 필요하면 Kubernetes Secret 이다.
- 이 `README.md` 는 Dockerfile 이 신뢰 저장소에 넣기 전에 지운다.
