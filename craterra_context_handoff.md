# Craterra 프로젝트 — 새 채팅 컨텍스트
> 이 내용을 새 채팅 첫 메시지에 붙여넣으면 이어서 작업 가능합니다.
> 마지막 업데이트: 2026-06-07

---

## 나는 지금 Craterra라는 서비스를 개발 중이야. 아래가 지금까지 확정된 내용 전부야.

---

### 서비스 정의
"알고리즘 말고, 진짜 디깅 — 곡 하나로 숨겨진 음악을 발굴하는 도구"

- 음악을 소유하거나 스트리밍하지 않는다 → 라이선싱 리스크 없음
- 발견 → 외부 플랫폼 연결 레이어에서만 작동한다
- 글로벌 타겟, 익명 세션(로그인 없음), 언어 장벽 없음(곡 이름 하나로 작동)

---

### 기술 스택 (확정)
| 역할 | 기술 |
|---|---|
| 프론트 | HTML/JS (React는 나중에) |
| 백엔드 | Python FastAPI |
| DB | PostgreSQL (Supabase 무료티어) |
| 배포 | Railway (백엔드) + Vercel (프론트) |
| AI | DeepSeek via OpenRouter |

- 로컬 LLM 안 씀 (민감 데이터 없음, 트래픽 낮음, 비용 비효율)
- Hermes Agent 같은 에이전트 프레임워크 안 씀 (오버스펙)
- 초기 비용: 거의 0원 (DeepSeek API 비용만)
- OpenRouter 기본 모델: `deepseek/deepseek-v4-flash`
- OpenRouter fallback/비용 절감 실험 모델: `qwen/qwen3-30b-a3b-instruct-2507`
- 이유: Craterra는 후보 풀 기반 큐레이션이라 초대형 모델은 필수는 아니지만, 추천 이유의 설득력과 첫인상 품질이 제품 핵심이라 DeepSeek 계열을 기본값으로 잡는다. `deepseek/deepseek-v4-flash`는 OpenRouter 기준 저렴하고 structured output을 지원해 MVP 기본 모델로 적합하다

---

### API 전략 (확정) — 기능별 역할 분담

| 기능 | 메인 | Fallback |
|---|---|---|
| 곡 검증 | Deezer | MusicBrainz → iTunes |
| 앨범아트 | Deezer | iTunes |
| 30초 미리듣기 | Deezer (MP3 직접) | iTunes |
| 풀 미리듣기 | YouTube iframe embed | — |
| 희귀도 점수 | Last.fm 청취수 + Deezer fan count | — |
| 추천 후보 풀 | Last.fm 유사 아티스트 + ListenBrainz | — |
| 프로듀서/레이블 관계 | MusicBrainz | — |
| 구매 연결 | Bandcamp 어필리에이트 | Apple Music 어필리에이트 |

**Last.fm API 비용/정책 메모 (중요):**
- Last.fm 계정 생성 및 API key 발급은 개발 시작 기준 무료로 진행 가능
- Last.fm Pro 구독은 API key 발급과 별개이며, Craterra MVP 개발에는 필요 없음
- 단, Last.fm 공식 API 문서는 상업용 또는 연구/학술 목적 사용 시 사전 문의를 안내함
- Craterra를 공개 런칭하거나 수익화하기 전 `partners@last.fm` 문의 또는 Last.fm 의존도 축소 전략 검토 필요
- MVP 개발 중에는 `LASTFM_API_KEY`를 `.env`에 넣어 후보 풀/희귀도 점수용으로 사용

**제외 확정:**
- Spotify: 2026.02 대폭 제한, Dev Mode 5명 제한, Extended 25만 MAU 필요 → 완전 제외
- iTunes: Deezer로 대체, 검증 fallback + Apple Music 어필리에이트 채널로만 잔존
- SoundCloud: API 안정성 불투명 → Later
- 로컬 LLM / Hermes Agent: 오버스펙, 비용 비효율 → 완전 제외

**AI 추천 흐름:**
```
Last.fm + ListenBrainz로 실제 데이터 기반 후보 풀 구성
    ↓
DeepSeek가 후보 풀에서 큐레이션 + 이유 생성
    ↓
Deezer로 검증 (실존 확인 + 아트 + 미리듣기 URL 획득)
```
→ AI 단독 환각 방지, 검증된 곡만 카드에 노출

---

### 백엔드 엔드포인트 (FastAPI)
| 메서드 | 경로 | 역할 |
|---|---|---|
| POST | `/dig` | 곡 + 파라미터 → 후보 풀 구성 → AI 큐레이션 → 추천 반환 |
| POST | `/feedback` | session_id + song + vote 저장 |
| GET | `/validate` | Deezer → MusicBrainz → iTunes 순 곡 검증 |

**현재 구현 상태 (로컬 MVP):**
- FastAPI 앱 기본 구조 구현 완료
- `/validate`: Deezer → MusicBrainz → iTunes fallback 구현 완료
- `/dig`: Deezer 입력곡 정규화 → Last.fm 유사곡 후보 풀 → OpenRouter 큐레이션 → Deezer/MusicBrainz/iTunes fallback 검증 → 추천 카드 반환 구현 완료
- `/feedback`: Supabase 전 단계로 로컬 `data/feedback.jsonl` 저장 구현 완료
- 세션 취향 반영: `session_id` 기준 좋아요/싫어요 트랙/아티스트를 다음 `/dig` 프롬프트에 주입
- 프론트 MVP: FastAPI가 `/`에서 `frontend/index.html`을 서빙, 입력 → 추천 카드 → 좋아요/스킵 피드백 가능
- 프론트 컨트롤: 점프 강도, region, era, challenge mode, 추천 카드의 이 곡으로 계속 디깅 버튼 구현
- 디깅 히스토리: `session_id` 기준 로컬 `data/dig_history.jsonl` 저장 구현 완료
- 희귀도 배지: Last.fm playcount/listeners 기반 후보 풀 상대 희귀도 점수 계산, 추천 카드에 `Deepest here` / `Less played` / `Mid-known` / `Obvious` 라벨 노출

---

### DB 설계 (Supabase)
```sql
-- 피드백 (협업 필터링 재료)
feedback (
  id            uuid PRIMARY KEY,
  session_id    text,
  song_name     text,
  artist_name   text,
  vote          boolean,     -- true=좋아요, false=싫어요
  created_at    timestamp
)

-- 디깅 히스토리 (취향 지형도 재료 — Phase 2+, MVP엔 로컬 저장)
dig_history (
  id            uuid PRIMARY KEY,
  session_id    text,
  root_song     text,
  chain         jsonb,       -- 디깅 체인 트리
  params        jsonb,       -- distance_level, region 등
  created_at    timestamp
)

-- 디깅 패턴 캐시 (Hermes 스킬 개념 차용)
dig_patterns (
  id            uuid PRIMARY KEY,
  input_genre   text,        -- 입력곡 장르/감성 태그
  jump_to       text,        -- 성공한 점프 방향
  success_rate  float,       -- 좋아요 / 전체 노출
  sample_count  int,         -- 통계 신뢰도
  updated_at    timestamp
)

-- 세션 취향 프로필 (Hermes 영구 메모리 개념 차용)
session_profile (
  session_id    text PRIMARY KEY,
  liked_tags    jsonb,       -- 좋아요 누적 태그
  disliked_tags jsonb,       -- 싫어요 누적 태그
  updated_at    timestamp
)
```

---

### AI 프롬프트 파라미터 (확정)
| 파라미터 | 값 |
|---|---|
| `distance_level` | 1(안전) ~ 5(모험) |
| `region` | KR / JP / BR / EU 등 |
| `era` | 1960s ~ 2020s |
| `challenge_mode` | true / false |
| `mood_tags` | 새벽 / 고독 / 드라이브 등 |

**프롬프트 원칙:**
- 메인스트림 제외, 스트리밍 수 적은 곡 우선
- 장르 경계 넘나들기 / 프로듀서·레이블·시대 라인 타기
- 각 추천마다 연결 이유 1~2문장 필수
- 세션 싫어요 패턴 → 프롬프트 제외 규칙으로 주입
- 세션 좋아요 패턴 → 프롬프트 강화 규칙으로 주입
- 성공한 dig_patterns → 후보 우선순위 부스트

---

### Hermes 개념 차용 — 디깅 학습 루프

Hermes Agent의 메커니즘을 GPU/에이전트 없이 Supabase + 프롬프트만으로 재구현:

| Hermes 원본 | Craterra 차용 | 구현 위치 |
|---|---|---|
| 자동 스킬 생성 | 성공 디깅 패턴 캐싱 | `dig_patterns` 테이블 |
| 영구 메모리 | 익명 세션 취향 프로필 | `session_profile` 테이블 |
| 자기개선 루프 | 피드백 → 프롬프트 규칙 진화 | `/dig` 프롬프트 조합 로직 |
| 스킬 검색 | 유사 입력 → 캐시 패턴 매칭 부스트 | `/dig` 전처리 |

**학습 루프 흐름:**
```
유저 디깅
    ↓
피드백 수집 (feedback 테이블)
    ↓
성공 패턴 집계 (dig_patterns 업데이트)
    ↓
다음 유사 입력 → 캐시 패턴 우선 적용
    ↓
더 나은 추천 → 더 많은 피드백 → 선순환
```

---

### 핵심 UX 흐름
```
곡 이름 입력
  + [선택] 점프 강도 슬라이더 (1~5)
  + [선택] 무드 키워드 태그
        ↓
  후보 풀 구성 (Last.fm + ListenBrainz)
        ↓
  AI 큐레이션 (DeepSeek) + 이유 생성
        ↓
  Deezer 검증 + 아트 + 미리듣기 URL
        ↓
  추천 카드 3~5개
    - 앨범아트 (Deezer)
    - 추천 이유 1~2줄 (AI 생성)
    - 희귀도 배지 (Last.fm 청취수 + Deezer fan count)
    - 30초 미리듣기 (Deezer MP3)
    - Bandcamp / Apple Music 링크
        ↓
  피드백 (좋아요/싫어요) → 서버 저장
  + [선택] 이 곡으로 계속 디깅 → 체인 트리 (로컬 저장)
```

---

### 차별화 기능 우선순위
**MVP 즉시:**
1. 추천 이유 카드 (AI 생성 연결 근거)
2. 희귀도 배지 (스트리밍 수 낮을수록 상단)
3. 세션 취향 프로필 (싫어요 패턴 즉시 반영)

**MVP+1:**
4. 점프 강도 슬라이더
5. 디깅 체인 트리 시각화
6. 디깅 패턴 캐시 (학습 루프 가동)

**런칭 바이럴 트리거:**
7. Challenge Mode (취향 반대 추천)
8. 디깅 일지 SNS 공유 카드

**Later:**
9. 지역 필터 / 시대 점프
10. 취향 지형도 시각화
11. 협업 필터링 (피드백 10만건+)

---

### 수익화 로드맵
- **Day 1:** Bandcamp 어필리에이트 (5~10%) + Apple Music 어필리에이트
- **Phase 2:** Craterra Pro ($4~6/월) + 아티스트 부스트 ($10~20/곡)
- **Phase 3:** 취향 데이터 B2B · 큐레이터 마켓플레이스 · 화이트라벨 API

---

### 다음 액션 (순서대로)
1. OpenRouter API 키 확보 (DeepSeek 접근)
2. DeepSeek 디깅 프롬프트 설계 + 파라미터 5종 테스트
3. FastAPI 백엔드 기본 구조 (`/dig`, `/feedback`, `/validate`)
4. Supabase 테이블 4종 생성 (feedback, dig_history, dig_patterns, session_profile)
5. Deezer + Last.fm + ListenBrainz + MusicBrainz 연동 레이어
6. 프론트 UI (입력 → 카드 → 피드백)
7. Bandcamp 어필리에이트 링크 삽입
8. Railway + Vercel 배포

---

### 기타 확정
- TuneMirror(Scriptable 위젯)는 별도 유지, Craterra와 무관
- 홍보 1순위: r/ifyoulikeblank (구독자 90만)
- dig_history 서버 저장은 Phase 2(계정 생기면)로 미룸, MVP엔 로컬 스토리지만

---

*여기서부터 이어서 작업해줘.*
