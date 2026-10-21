# Release Preflight · 开源项目发布检查

**发布前，一次查清容易漏掉的小问题。**

[English](README.md) · [检查规则与范围](docs/rules.md) · [参与贡献](CONTRIBUTING.md) · [更新日志](CHANGELOG.md)

给小型开源项目维护者使用的离线命令行工具。集中检查版本、更新日志、
本地文档链接、项目文档、Git 工作区及发布文件 SHA-256，生成中英文终端报告、
JSON 或可独立分享的 HTML 报告。

当前为 **v0.1.0 alpha 初始版本**，尚未建立广泛使用和长期维护记录。
运行不依赖第三方 Python 库，不需要账号、API Key 或联网。

## 立即使用

需要 Python 3.11 或更高版本。在解压后的源码目录打开终端：

```powershell
python -B -m release_preflight . --release 0.1.0 --lang zh
python -B -m release_preflight "D:\你的项目" --lang zh --format html --output "D:\发布检查.html"
```

报告必须保存在被检查项目之外，且目标文件不能已经存在。
生成后手动打开 HTML；工具不会打开或切换浏览器窗口。
如果检查的是没有 `.git` 的源码压缩包，可明确加入 `--skip-git`。

也可以用标准库打包为单文件（仍需要 Python）：

```powershell
python scripts/build_zipapp.py ..\release-preflight.pyz
python -B ..\release-preflight.pyz "D:\你的项目" --lang zh
```

## 检查内容

| 项目 | 检查结果 |
| --- | --- |
| 版本号 | 根目录 package.json / pyproject.toml 静态版本是否一致、是否符合指定版本 |
| 更新日志 | 是否有本次版本对应的 Markdown 标题 |
| 文档链接 | 常见 Markdown 本地文件和图片链接是否存在；报告定位到行 |
| 开源文档 | README、许可证是否非空；提醒补充贡献指南和安全政策 |
| Git 工作区 | 是否有未提交或未跟踪的改动；是否有提交记录 |
| 发布文件 | 对显式指定的文件计算 SHA-256 和大小 |

未检查的内容会单独列出。远程网址、页内锚点、完整 CommonMark 语法、
应用功能、安全漏洞和许可证合法性不在首版验证范围内。
版本按字符串比较，不会执行项目的动态版本脚本。

## 常用参数

```powershell
python -B -m release_preflight . --release 0.1.0 --strict --lang zh
python -B -m release_preflight . --format json --output ..\检查结果.json
python -B -m release_preflight . --asset dist\应用.zip --lang zh
python -B -m release_preflight . --exclude generated --exclude snapshots
```

`--strict` 将提醒也作为失败；`--exclude` 接受目录名，不接受路径或通配符。
相对 `--asset` 路径以被扫描的项目根目录为准。
退出码：`0` 通过所选检查，`1` 有失败或严格模式提醒，`2` 使用/路径错误，`130` 中断。

## 开发

```powershell
python -B -m unittest discover -s tests -v
```

GitHub Actions 配置覆盖 Windows、Linux、macOS 及 Python 3.11/3.14；
在线运行结果需发布后查看，不能用配置文件代替验收。

维护者：**cyhandzxy**。计划公开仓库：
[cyhandzxy/release-preflight](https://github.com/cyhandzxy/release-preflight)。
采用 [MIT 许可证](LICENSE)。欢迎带有最小复现的缺陷反馈和小范围改进。
