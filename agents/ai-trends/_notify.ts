/**
 * 报告分发：把每日生成的报告推送到手机 / 群机器人。
 *
 * 全部通过环境变量开启，一个都不配就跳过，不会影响主流程。
 * 在 EdgeOne 控制台 → 项目 → 环境变量 里添加即可：
 *
 *   NOTIFY_WECOM      企业微信群机器人 webhook（推荐，手机能直接收到）
 *   NOTIFY_DINGTALK   钉钉群机器人 webhook（注意把「加签」关掉或另配）
 *   NOTIFY_FEISHU     飞书群机器人 webhook
 *   NOTIFY_BARK       Bark 推送地址，形如 https://api.day.app/你的KEY
 *   NOTIFY_PUSHPLUS   PushPlus token（微信 / QQ 都能用）
 *   NOTIFY_PUSHPLUS_CHANNEL  可选 wechat（默认）或 qq；填 qq 时走 QQ 机器人
 *   NOTIFY_QMSG       Qmsg酱 key（另一条 QQ 推送路线）
 *   NOTIFY_QMSG_QQ    接收消息的 QQ 号
 *   NOTIFY_WEBHOOK    自定义 webhook，会把报告 JSON POST 过去
 *
 *   NOTIFY_ON_SCHEDULE_ONLY  设为 1 时只在定时任务里推送，手动生成不推
 *   NOTIFY_SITE_URL          报告站点地址，默认 https://aitrend.lxyblog.top
 */
import type { TrendReport } from './_types.js';

export interface NotifyResult {
  channel: string;
  ok: boolean;
  detail?: string;
}

type Env = Record<string, string | undefined>;

const DEFAULT_SITE = 'https://aitrend.lxyblog.top';

function siteUrl(env: Env): string {
  return (env.NOTIFY_SITE_URL || DEFAULT_SITE).replace(/\/$/, '');
}

function dayLabel(iso: string): string {
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return iso.slice(0, 10);
  // 统一按北京时间展示
  const bj = new Date(t.getTime() + 8 * 3600 * 1000);
  return `${bj.getUTCMonth() + 1} 月 ${bj.getUTCDate()} 日`;
}

/** 纯文本版（用于飞书、自定义 webhook、Bark、QQ） */
export function buildText(report: TrendReport, env: Env): string {
  const head = report.status === 'success' ? 'AI 趋势日报' : 'AI 趋势日报（生成异常）';
  const lines = [
    `${head} · ${dayLabel(report.generatedAt)}`,
    '',
    report.summary || '（本期没有摘要）',
    '',
  ];

  const top = (report.trends || []).slice(0, 3);
  if (top.length) {
    lines.push('本期看点：');
    top.forEach((t, i) => {
      lines.push(`${i + 1}. ${t.category}：${t.count} 条 — ${(t.summary || '').slice(0, 60)}`);
    });
    lines.push('');
  }

  if (typeof report.itemCount === 'number') {
    lines.push(`共 ${report.itemCount} 条资讯，新增 ${report.newItemCount ?? 0} 条。`);
  }
  if (report.error) lines.push(`错误：${report.error}`);
  lines.push('', `查看完整报告：${siteUrl(env)}`);
  return lines.join('\n');
}

/** Markdown 版（企业微信 / 钉钉 / PushPlus 微信用） */
export function buildMarkdown(report: TrendReport, env: Env): string {
  const head = report.status === 'success' ? '## AI 趋势日报' : '## AI 趋势日报（生成异常）';
  const lines = [`${head}`, `> ${dayLabel(report.generatedAt)} · 共 ${report.itemCount ?? 0} 条`, '', report.summary || '_本期没有摘要_', ''];

  const top = (report.trends || []).slice(0, 3);
  if (top.length) {
    lines.push('**本期看点**');
    top.forEach((t, i) => lines.push(`${i + 1}. **${t.category}**（${t.count} 条）${(t.summary || '').slice(0, 60)}`));
    lines.push('');
  }

  if (report.error) lines.push(`**错误**：${report.error}`, '');
  lines.push(`[查看完整报告](${siteUrl(env)})`);
  return lines.join('\n');
}

async function postJson(url: string, body: unknown, headers: Record<string, string> = {}): Promise<void> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json', ...headers },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} ${(await res.text()).slice(0, 120)}`);
}

async function sendWecom(webhook: string, md: string): Promise<void> {
  await postJson(webhook, { msgtype: 'markdown', markdown: { content: md } });
}

async function sendDingtalk(webhook: string, title: string, md: string): Promise<void> {
  await postJson(webhook, { msgtype: 'markdown', markdown: { title, text: md } });
}

async function sendFeishu(webhook: string, text: string): Promise<void> {
  await postJson(webhook, { msg_type: 'text', content: { text } });
}

async function sendBark(base: string, title: string, text: string): Promise<void> {
  const url = `${base.replace(/\/$/, '')}/${encodeURIComponent(title)}/${encodeURIComponent(text)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

async function sendPushplus(token: string, title: string, md: string): Promise<void> {
  await postJson('https://www.pushplus.plus/send', { token, title, content: md, template: 'markdown' });
}

/** QQ 渠道：QQ 原生 Markdown 不支持代码块和 HTML，用纯文本最稳 */
async function sendPushplusQQ(token: string, title: string, text: string): Promise<void> {
  await postJson('https://www.pushplus.plus/send', {
    token,
    title,
    content: text,
    template: 'txt',
    channel: 'qq',
  });
}

/** Qmsg酱：极简的 QQ 单聊推送 */
async function sendQmsg(key: string, qq: string, text: string): Promise<void> {
  const body = new URLSearchParams({ msg: text, qq });
  const res = await fetch(`https://qmsg.zendee.cn/v3/send/${key}`, {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} ${(await res.text()).slice(0, 120)}`);
}

/**
 * 分发一份报告。任何渠道失败都不抛错，只记录结果。
 * 返回每个渠道的执行情况，便于在日志里排查。
 */
export async function notifyReport(report: TrendReport, env: Env, isSchedule = false): Promise<NotifyResult[]> {
  if (env.NOTIFY_ON_SCHEDULE_ONLY === '1' && !isSchedule) return [];

  const title = `AI 趋势日报 · ${dayLabel(report.generatedAt)}`;
  const text = buildText(report, env);
  const md = buildMarkdown(report, env);
  const results: NotifyResult[] = [];

  const tasks: Array<[string, () => Promise<void>]> = [];
  if (env.NOTIFY_WECOM) tasks.push(['wecom', () => sendWecom(env.NOTIFY_WECOM!, md)]);
  if (env.NOTIFY_DINGTALK) tasks.push(['dingtalk', () => sendDingtalk(env.NOTIFY_DINGTALK!, title, md)]);
  if (env.NOTIFY_FEISHU) tasks.push(['feishu', () => sendFeishu(env.NOTIFY_FEISHU!, text)]);
  if (env.NOTIFY_BARK) tasks.push(['bark', () => sendBark(env.NOTIFY_BARK!, title, text)]);
  if (env.NOTIFY_PUSHPLUS) {
    const ppChannel = (env.NOTIFY_PUSHPLUS_CHANNEL || 'wechat').toLowerCase();
    tasks.push([
      `pushplus-${ppChannel}`,
      ppChannel === 'qq'
        ? () => sendPushplusQQ(env.NOTIFY_PUSHPLUS!, title, text)
        : () => sendPushplus(env.NOTIFY_PUSHPLUS!, title, md),
    ]);
  }
  if (env.NOTIFY_QMSG) tasks.push(['qmsg', () => sendQmsg(env.NOTIFY_QMSG!, env.NOTIFY_QMSG_QQ || '', text)]);
  if (env.NOTIFY_WEBHOOK) tasks.push(['webhook', () => postJson(env.NOTIFY_WEBHOOK!, report)]);

  for (const [channel, run] of tasks) {
    try {
      await run();
      results.push({ channel, ok: true });
    } catch (e) {
      results.push({ channel, ok: false, detail: e instanceof Error ? e.message : String(e) });
    }
  }

  return results;
}
