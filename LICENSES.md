# Data and License Admission

□ 현재 데이터 상태

• `data/synthetic_cases.json`은 이 작업에서 새로 작성한 합성 fixture다.
  - 실제 환자, 의료기록, 사용자 건강데이터, 비공개 대회 증례는 포함하지 않는다.
  - fixture는 평가 하네스의 기계적 동작을 검증할 뿐 임상 검증 자료가 아니다.

□ 외부 데이터 후보

• Synthea는 합성 환자 생성기 후보로만 등록했다.
  - Synthea 소스는 Apache-2.0으로 제공되며, 생성 결과의 FHIR 형식과 용어에는 별도 조건이 있을 수 있다.
  - 아직 저장소에 Synthea 생성물, 코드, 모델, 용어집을 넣지 않았다.
  - 도입할 때는 정확한 release/commit, 생성 명령·seed, NOTICE, 출력 형식과 용어의 라이선스를 source manifest에 고정한다.

□ 반입 금지

• 실제 환자 데이터, 비공개 대회 증례, 평가 로그, 계정·API 토큰, 원문 대화
• 출처 또는 연구 출판 이용 조건이 불명확한 데이터·모델·도구
• 공개 샘플과 holdout을 섞어 성능으로 표현한 결과
