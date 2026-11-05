#!/usr/bin/env python3
"""抓取最新的 AI 趋势报告，渲染成 PDF，发到邮箱。

设计要点：
- 不依赖云函数：跑在 GitHub Actions 上，有完整 Linux、可 apt 装中文字体、可自由发 SMTP
- PDF 用 Chromium headless 打印，中文字体由系统提供，不用往仓库塞几 MB 字体
- 邮件用 QQ 邮箱 SMTP（授权码），附件是 PDF

环境变量：
  MAIL_USER   发件邮箱，如 123456@qq.com
  MAIL_PASS   邮箱「授权码」，不是登录密码
  MAIL_TO     收件邮箱，留空则发给 MAIL_USER 自己
  REPORT_URL  报告 API，默认线上地址
  SMTP_HOST   默认 smtp.qq.com
  SMTP_PORT   默认 465（SSL）
  CHROME      浏览器可执行文件路径，默认 google-chrome
"""

import html
import json
import os
import re
import shutil
import smtplib
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.request import Request, urlopen

def _load_env_file() -> None:
    """从 scripts/mail.env 读取邮件配置（本机定时任务用，云端走环境变量）。"""
    path = Path(__file__).with_name('mail.env')
    if not path.exists():
        return
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


_load_env_file()

REPORT_URL = os.environ.get('REPORT_URL', 'https://aitrend.lxyblog.top/ai-trends/latest')
BEIJING = timezone(timedelta(hours=8))


def fetch_report() -> dict:
    req = Request(REPORT_URL, headers={'user-agent': 'ai-trends-pdf/1.0'})
    with urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    if not data.get('reportMarkdown'):
        raise SystemExit('报告为空，可能还没生成过')
    return data


def md_to_html(md: str) -> str:
    """够用就好的 markdown 渲染：标题、列表、引用、粗体、链接、代码块。"""
    out = []
    in_list = False

    def inline(text: str) -> str:
        text = html.escape(text)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        text = re.sub(r'\[(.+?)\]\((https?://[^\s)]+)\)', r'<a href="\2">\1</a>', text)
        # 裸链接也变成可点的
        text = re.sub(r'(?<!["=>])(https?://[^\s<]+)', r'<a href="\1">\1</a>', text)
        return text

    for raw in md.split('\n'):
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith('```'):
            out.append('</ul>' if in_list else '')
            in_list = False
            out.append('<pre>')
            continue

        if not stripped:
            if in_list:
                out.append('</ul>')
                in_list = False
            continue

        m = re.match(r'^(#{1,4})\s+(.*)$', stripped)
        if m:
            if in_list:
                out.append('</ul>')
                in_list = False
            level = len(m.group(1))
            out.append(f'<h{level}>{inline(m.group(2))}</h{level}>')
            continue

        if stripped.startswith(('- ', '* ')):
            if not in_list:
                out.append('<ul>')
                in_list = True
            out.append(f'<li>{inline(stripped[2:])}</li>')
            continue

        if stripped.startswith('> '):
            if in_list:
                out.append('</ul>')
                in_list = False
            out.append(f'<blockquote>{inline(stripped[2:])}</blockquote>')
            continue

        if in_list:
            out.append('</ul>')
            in_list = False
        out.append(f'<p>{inline(stripped)}</p>')

    if in_list:
        out.append('</ul>')
    return '\n'.join(x for x in out if x)


PAGE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>{title}</title>
<style>
  @page {{ size: A4; margin: 18mm 16mm 16mm; }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "Noto Sans CJK SC", "Noto Sans SC", "Microsoft YaHei", sans-serif;
    font-size: 11pt; line-height: 1.75; color: #1a1a1a; margin: 0;
  }}
  header {{ border-bottom: 2px solid #111; padding-bottom: 10px; margin-bottom: 18px; }}
  header h1 {{ font-size: 19pt; margin: 0 0 6px; letter-spacing: .5px; }}
  header .meta {{ font-size: 9pt; color: #666; }}
  h1 {{ font-size: 15pt; margin: 18px 0 8px; }}
  h2 {{ font-size: 13pt; margin: 18px 0 8px; padding-left: 8px; border-left: 3px solid #111; }}
  h3 {{ font-size: 11.5pt; margin: 14px 0 6px; }}
  p {{ margin: 0 0 8px; }}
  ul {{ margin: 0 0 10px; padding-left: 20px; }}
  li {{ margin-bottom: 4px; }}
  blockquote {{ margin: 10px 0; padding: 6px 12px; background: #f5f5f5; border-left: 3px solid #ccc; color: #444; }}
  a {{ color: #0b5cad; text-decoration: none; word-break: break-all; }}
  code {{ background: #f2f2f2; padding: 1px 4px; border-radius: 3px; font-size: 10pt; }}
  pre {{ background: #f7f7f7; padding: 10px; border-radius: 4px; overflow: hidden; font-size: 9.5pt; }}
  h2, h3 {{ page-break-after: avoid; }}
  li, p {{ page-break-inside: avoid; }}
  footer {{ margin-top: 22px; padding-top: 8px; border-top: 1px solid #ddd; font-size: 8.5pt; color: #888; }}
</style></head>
<body>
<header>
  <h1>{title}</h1>
  <div class="meta">{meta}</div>
</header>
{body}
<footer>由 ai-trends 自动生成 · {site}</footer>
</body></html>
"""


def build_html(report: dict) -> tuple[str, str]:
    ts = report.get('generatedAt') or ''
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(BEIJING)
        date_cn = f'{dt.year} 年 {dt.month} 月 {dt.day} 日'
    except Exception:
        dt = datetime.now(BEIJING)
        date_cn = f'{dt.year} 年 {dt.month} 月 {dt.day} 日'

    title = f'AI 趋势日报 · {dt.month} 月 {dt.day} 日'
    meta = f"{dt.strftime('%Y-%m-%d %H:%M')} · 共 {report.get('itemCount', 0)} 条资讯"
    if report.get('newItemCount') is not None:
        meta += f" · 新增 {report['newItemCount']} 条"

    site = os.environ.get('SITE_LABEL', 'aitrend.lxyblog.top')
    page = PAGE.format(
        title=html.escape(title),
        meta=html.escape(meta),
        body=md_to_html(report['reportMarkdown']),
        site=html.escape(site),
    )
    return title, page


def html_to_pdf(html_text: str, out_pdf: Path) -> None:
    # 依次尝试：显式指定 > GitHub Actions 预装的 chrome > chromium
    candidates = [os.environ.get('CHROME'), 'google-chrome', 'google-chrome-stable',
                  'chromium', 'chromium-browser', '/usr/bin/google-chrome']
    chrome = next((c for c in candidates if c and shutil.which(c)), None)
    if not chrome:
        raise SystemExit('没找到 Chrome/Chromium，无法打印 PDF')
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / 'report.html'
        src.write_text(html_text, encoding='utf-8')
        cmd = [
            chrome, '--headless=new', '--disable-gpu', '--no-sandbox',
            '--no-pdf-header-footer', f'--print-to-pdf={out_pdf}',
            src.as_uri(),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if not out_pdf.exists() or out_pdf.stat().st_size < 1024:
            raise SystemExit(f'PDF 生成失败（{chrome}）：{proc.stderr[-500:]}')


def send_mail(subject: str, html_body: str, pdf_path: Path, report: dict) -> None:
    user = os.environ['MAIL_USER']
    password = os.environ['MAIL_PASS']
    to_addr = os.environ.get('MAIL_TO') or user

    msg = MIMEMultipart()
    msg['From'] = user
    msg['To'] = to_addr
    msg['Subject'] = Header(subject, 'utf-8')

    fallback = (report.get('summary') or '')[:800]
    msg.attach(MIMEText(
        f'<p>{html.escape(fallback)}</p><p>完整报告见附件 PDF。</p>',
        'html', 'utf-8'))

    with open(pdf_path, 'rb') as f:
        part = MIMEApplication(f.read(), _subtype='pdf')
    part.add_header('Content-Disposition', 'attachment',
                    filename=('utf-8', '', pdf_path.name))
    msg.attach(part)

    host = os.environ.get('SMTP_HOST', 'smtp.qq.com')
    port = int(os.environ.get('SMTP_PORT', '465'))
    with smtplib.SMTP_SSL(host, port, timeout=60) as s:
        s.login(user, password)
        s.send_message(msg)


def main() -> None:
    report = fetch_report()
    title, page = build_html(report)

    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / f"AI趋势日报-{datetime.now(BEIJING).strftime('%Y%m%d')}.pdf"
        html_to_pdf(page, pdf)
        size_kb = pdf.stat().st_size // 1024
        print(f'PDF 生成成功：{pdf.name}（{size_kb} KB）')

        if os.environ.get('DRY_RUN') == '1':
            keep = Path('preview.pdf')
            keep.write_bytes(pdf.read_bytes())
            print('DRY_RUN=1，已保存为 preview.pdf，不发送邮件')
            return

        send_mail(title, page, pdf, report)
        print('邮件已发送')


if __name__ == '__main__':
    main()
