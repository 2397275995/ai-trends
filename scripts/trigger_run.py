#!/usr/bin/env python3
"""触发一次采集，并等待「确实产生了新报告」。

为什么需要这个脚本：
- 直接 POST /ai-trends/run 返回的是 SSE 流，断开连接可能让流水线中断，
  所以这里把流读到底（保持连接）。
- 触发后不能只看「最新报告有没有内容」，要对比「生成时间是否变了」，
  否则会把上一次的旧报告当成新的发出去。
"""

import json
import os
import sys
import uuid
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE = 'https://aitrend.lxyblog.top'
LATEST = f'{BASE}/ai-trends/latest'
RUN = f'{BASE}/ai-trends/run'

PAYLOAD = {
    '_schedule': True,
    'trigger': 'schedule',
    'sources': ['hackernews', 'devto', 'web'],
    'limit': 30,
}

STREAM_TIMEOUT = 1500     # 流水线本身最长 20 分钟，给足余量
POLL_TIMEOUT = 600        # 流结束后最多再等 10 分钟落库


def latest() -> dict:
    with urllib.request.urlopen(LATEST, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


def ts_of(report: dict) -> str:
    return report.get('generatedAt') or ''


def main() -> None:
    before = latest()
    before_ts = ts_of(before)
    print(f'触发前的最新报告：{before_ts}（{before.get("itemCount")} 条）', flush=True)

    body = json.dumps(PAYLOAD).encode('utf-8')
    # 接口强制要求这个头（6-36 位、字母数字和 -_.），否则直接 400
    conv_id = os.environ.get('MAKERS_CONVERSATION_ID') or f'daily-{uuid.uuid4().hex[:24]}'
    req = urllib.request.Request(
        RUN, data=body,
        headers={
            'content-type': 'application/json',
            'accept': 'text/event-stream',
            'makers-conversation-id': conv_id,
        },
        method='POST',
    )
    print(f'会话 ID：{conv_id}', flush=True)

    print('开始触发 /ai-trends/run，保持连接直到流水线结束…', flush=True)
    stages = []
    try:
        with urllib.request.urlopen(req, timeout=STREAM_TIMEOUT) as resp:
            for raw in resp:
                line = raw.decode('utf-8', 'replace').strip()
                if not line.startswith('data:'):
                    continue
                try:
                    evt = json.loads(line[5:].strip())
                except Exception:
                    continue
                stage = evt.get('stage')
                status = evt.get('status')
                if stage and status in ('done', 'failed'):
                    stages.append(f'{stage}:{status}')
                    print(f'  阶段 {stage} → {status}', flush=True)
    except urllib.error.HTTPError as e:
        print(f'触发失败，HTTP {e.code}：{e.read()[:200].decode("utf-8", "replace")}', flush=True)
        sys.exit(1)
    except Exception as e:
        print(f'流式连接中断：{e}', flush=True)
        # 不直接失败，下面还会轮询确认报告是否已生成

    print('流水线结束，开始确认报告是否落库…', flush=True)

    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        try:
            cur = latest()
            cur_ts = ts_of(cur)
            changed = cur_ts and cur_ts != before_ts
            print(f'  当前最新：{cur_ts} status={cur.get("status")} '
                  f'{"（已更新）" if changed else "（还是旧的）"}', flush=True)
            if changed and cur.get('status') == 'success':
                age = (datetime.now(timezone.utc)
                       - datetime.fromisoformat(cur_ts.replace('Z', '+00:00'))).total_seconds()
                if age < 1800:
                    print(f'✓ 拿到新报告，{int(age)} 秒前生成', flush=True)
                    return
        except Exception as e:
            print(f'  查询出错：{e}', flush=True)
        time.sleep(20)

    print('✗ 等待超时：没有检测到新报告，本次不发邮件。', flush=True)
    print('  可能原因：站点访问受限、模型额度不足、流水线报错。', flush=True)
    print(f'  阶段记录：{stages}', flush=True)
    sys.exit(1)


if __name__ == '__main__':
    main()
