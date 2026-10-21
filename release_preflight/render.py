"""Text and self-contained HTML output. Repository strings are always escaped."""

from html import escape

from .core import Report

LABELS = {
    "en": {"pass": "Passed", "warn": "Warnings", "fail": "Failed", "skip": "Not checked"},
    "zh": {"pass": "通过", "warn": "提醒", "fail": "失败", "skip": "未检查"},
}


def text_report(report: Report, lang: str = "en", strict: bool = False) -> str:
    lines = [f"Release Preflight | {report.project} | {report.release or '—'}", ""]
    for check in report.checks:
        message = check.zh if lang == "zh" else check.en
        source = (f" [{check.path}" + (f":{check.line}" if check.line else "") + "]") if check.path else ""
        lines.append(f"{check.status.upper():4} {message}{source}")
    lines.extend(["", " · ".join(f"{LABELS[lang][s]}: {n}" for s, n in report.counts.items()),
                  f"Exit code: {report.exit_code(strict)}" + (" (strict)" if strict else "")])
    for asset in report.assets:
        lines.append(f"SHA256 {asset['sha256']}  {asset['name']}")
    # Strip terminal-control characters from untrusted names and messages.
    return "".join(c if c in "\n\t" or (ord(c) >= 32 and ord(c) != 127) else "?" for c in "\n".join(lines)) + "\n"


def html_report(report: Report, lang: str = "en", strict: bool = False) -> str:
    chinese = lang == "zh"
    blocked = bool(report.exit_code(strict))
    title = ("发布检查需要处理" if blocked else "已通过所选检查") if chinese else ("Review before release" if blocked else "Selected checks passed")
    subtitle = "一次离线检查，整理发布前需要处理的事项。" if chinese else "An offline view of the details that matter before a release."
    rows = []
    for check in report.checks:
        source = check.path + (f":{check.line}" if check.line else "")
        rows.append(f'<article class="check {check.status}" data-status="{check.status}"><span class="badge">{LABELS[lang][check.status]}</span><div><h3>{escape(check.zh if chinese else check.en)}</h3><p><code>{escape(check.rule)}</code>{" · " + escape(source) if source else ""}</p></div></article>')
    cards = "".join(f'<div class="metric {s}"><strong>{n:02}</strong><span>{LABELS[lang][s]}</span></div>' for s, n in report.counts.items())
    asset_cards = "".join(f'<li><strong>{escape(a["name"])}</strong><span>{a["bytes"]:,} bytes</span><code>{a["sha256"]}</code></li>' for a in report.assets)
    assets = f'<section><h2>{"发布文件指纹" if chinese else "Artifact fingerprints"}</h2><ul class="assets">{asset_cards}</ul></section>' if asset_cards else ""
    all_label = "全部" if chinese else "All checks"
    buttons = f'<button type="button" class="active" data-filter="all" aria-pressed="true">{all_label}</button>' + "".join(f'<button type="button" data-filter="{s}" aria-pressed="false">{LABELS[lang][s]}</button>' for s in LABELS[lang])
    scope = ("检查结果只覆盖本工具列出的规则。它不代替功能测试、安全审计或发布批准。远程链接和页内锚点未检查；不会执行项目代码或联网。" if chinese else "Results cover the listed rules only. They do not replace functional tests, a security audit, or release approval. Remote links and anchors are not checked. Project code is never executed; no network requests are made.")
    return f'''<!doctype html>
<html lang="{"zh-CN" if chinese else "en"}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Release Preflight · {escape(report.project)}</title>
<style>
:root{{--ink:#152e3c;--muted:#627782;--paper:#f5f7f5;--line:#dce5e1;--green:#08765a;--amber:#8c5700;--red:#b12f3e}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.65 system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif}}header{{background:#142f3b;color:white;padding:38px max(24px,calc((100vw - 1000px)/2)) 50px}}.brand{{font-size:13px;letter-spacing:.15em;text-transform:uppercase;color:#95d7bf;font-weight:700}}h1{{font-size:clamp(30px,5vw,46px);line-height:1.2;letter-spacing:-.03em;margin:24px 0 14px}}.subtitle{{color:#c1d5dd;margin:0;max-width:660px}}.meta{{margin-top:28px;display:flex;flex-wrap:wrap;gap:10px}}.meta span{{border:1px solid #42606b;padding:5px 12px;border-radius:6px;overflow-wrap:anywhere}}main{{max-width:1048px;margin:auto;padding:0 24px 44px}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:-20px}}.metric{{background:white;border:1px solid var(--line);border-radius:10px;padding:20px 24px;box-shadow:0 5px 16px #142f3b08}}.metric strong{{display:block;font-size:34px;font-variant-numeric:tabular-nums;line-height:1.25}}.metric span{{color:var(--muted);font-size:13px}}.pass strong{{color:var(--green)}}.warn strong{{color:var(--amber)}}.fail strong{{color:var(--red)}}section{{margin-top:32px}}h2{{font-size:20px;margin:0 0 14px}}nav{{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0 16px}}button{{border:1px solid var(--line);background:white;padding:8px 15px;border-radius:7px;color:var(--ink);cursor:pointer;font:inherit;font-size:13px}}button:hover{{border-color:#08765a}}button:focus-visible{{outline:3px solid #4a9681;outline-offset:3px}}button.active{{background:var(--ink);border-color:var(--ink);color:white}}.checks{{border:1px solid var(--line);border-radius:10px;background:white;overflow:hidden}}.check{{display:flex;gap:18px;padding:18px 22px;border-bottom:1px solid var(--line);align-items:flex-start}}.check:last-child{{border-bottom:0}}.check[hidden]{{display:none}}.badge{{min-width:84px;text-align:center;background:#eef2f3;color:#566d79;font-size:12px;font-weight:650;border-radius:5px;padding:3px 8px;flex-shrink:0}}.pass .badge{{background:#e3f4ec;color:var(--green)}}.warn .badge{{background:#fff3d8;color:var(--amber)}}.fail .badge{{background:#fde9eb;color:var(--red)}}h3{{font-size:14px;font-weight:550;margin:0;overflow-wrap:anywhere}}.check p{{font-size:12px;color:var(--muted);margin:4px 0 0;overflow-wrap:anywhere}}code{{font-family:ui-monospace,Consolas,monospace}}.scope{{border-left:3px solid #95bbaa;padding:4px 0 4px 16px;color:var(--muted);font-size:13px;margin-top:28px}}.assets{{padding:0;list-style:none}}.assets li{{padding:18px 22px;border:1px solid var(--line);border-radius:8px;background:white;margin:10px 0}}.assets span{{float:right;color:var(--muted);font-size:12px}}.assets code{{display:block;word-break:break-all;font-size:12px;margin-top:8px}}footer{{font-size:12px;margin-top:28px;color:var(--muted)}}@media(max-width:600px){{.metrics{{grid-template-columns:repeat(2,1fr)}}.metric{{padding:16px}}.check{{gap:12px;padding:16px}}.badge{{min-width:68px}}.assets span{{float:none;display:block}}}}@media print{{header{{background:white;color:var(--ink);padding:0 0 20px}}.subtitle,.brand{{color:var(--ink)}}.metrics{{margin-top:0}}nav{{display:none}}main{{padding:0}}.check{{break-inside:avoid}}.check[hidden]{{display:flex}}}}
</style></head><body><header><div class="brand">Release Preflight / v0.1.0</div><h1>{title}</h1><p class="subtitle">{subtitle}</p><div class="meta"><span>{escape(report.project)}</span><span>{escape(report.release or "—")}</span><span>{"严格模式" if strict and chinese else "Strict mode" if strict else "标准模式" if chinese else "Standard mode"}</span></div></header>
<main><div class="metrics">{cards}</div><section aria-label="{"检查明细" if chinese else "Check details"}"><nav aria-label="{"筛选结果" if chinese else "Filter results"}">{buttons}</nav><div class="checks">{"".join(rows)}</div></section>{assets}<p class="scope">{scope}</p><footer>Release Preflight · MIT · {"离线生成，可直接分享此 HTML 文件" if chinese else "Generated offline. Share this HTML file directly."}</footer></main>
<script>document.querySelectorAll('button[data-filter]').forEach(button=>button.addEventListener('click',()=>{{const filter=button.dataset.filter;document.querySelectorAll('.check').forEach(row=>row.hidden=filter!=='all'&&row.dataset.status!==filter);document.querySelectorAll('button[data-filter]').forEach(item=>{{const active=item===button;item.classList.toggle('active',active);item.setAttribute('aria-pressed',String(active));}});}}));</script></body></html>'''
