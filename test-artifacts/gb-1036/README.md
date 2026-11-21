# gb-1036 坏别名隔离与待补门牌对验证

无需 Docker，本地 Python3.11（需 fastapi/sqlalchemy/scikit-learn/httpx）+ Node 即可运行；脚本使用独立 SQLite 库（写到 /tmp/addr-test）与假 Redis，不触碰 compose 卷。

```bash
python3 test-artifacts/gb-1036/test_integration.py   # worker/服务/修订号/脱版/幂等等端到端
python3 test-artifacts/gb-1036/test_http.py          # TestClient 路由、角色与 409 拦截
node test-artifacts/gb-1036/fe.mjs                   # 归并核验页渲染（坏别名/暂用分/待补/脱版）
```

覆盖点：

1. “十十号”坏别名不再让整批匹配报错，坏别名落 `pending_fix` 并进入 `bad_aliases` 清单。
2. 漏比坏别名的门牌对即使有暂用分、或未出候选，均标 `pending` 且带 `missed_alias_ids`。
3. 待补门牌对建提案返回 409；补正为仍坏的文本同样 409；viewer 无补正权限（403）。
4. 补正/登记抬升 Registry 修订号；重算后旧批次置 `superseded`，新批次待补清除，守卫不采信旧分与旧待补状态。
5. 同批次重放不新增候选，`uq_candidate_run_pair` 唯一约束兜底。
