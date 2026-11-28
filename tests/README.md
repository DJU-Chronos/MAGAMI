# tests

테스트와 정확도 평가 스크립트를 보관합니다.

- 정확도 평가는 `data/ground_truth/eval/`의 정답 자료와 AI 결과를 비교합니다. 기준은 [docs/schema.md](../docs/schema.md)를 따릅니다.

## 실행

```bash
python -m unittest discover -s tests
```

단위 테스트는 Gemini를 가짜 객체로 대신하므로 API 키 없이 실행된다.
