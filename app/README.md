# 校园办事与入学助手 · Flutter 客户端（v1）

师生共用的校园办事与入学助手。Android + iOS 同一套源码，v1 不做微信小程序。

工程根目录：`/workspace/campus-assistant/app/`

## 产品要点

- 首页只有一句提问 + 待办列表（作业、志愿者招募、报到、请假、奖助都进同一待办；新生顶部有「入学与报到」分组）。没有九宫格功能仓。
- 对话结果页固定三块：结论、依据卡片、去办理/生成草稿。依据可点开原文高亮。冲突会写明以哪份哪个学期为准。无依据不编造并给出人工入口。无权限只提示需辅导员查看，不打码漏文。
- 任何提交前必须经过确认页。系统不代替学生确认、不代替老师审批。
- App 不内置大模型；离线不能回答知识问题；设备只缓存会话摘要与待办摘要、以及附件缩略图。规则留在服务器。

## 指向服务器

- 默认源站：`http://8.148.186.220`
- 业务接口前缀：`/api/v1`
- 健康检查：`GET /health`（根路径，不带 `/api/v1`）
- 登录后可在「我的档案」查看当前地址；登录页可展开「服务器设置」修改并检查连接。
- JWT 只写入安全存储（Keychain / EncryptedSharedPreferences），不打包任何服务器 `.env` 或密钥。
- 演示账号见 `docs/DEMO_ACCOUNTS.md`。登录页可点选学生/教师/辅导员演示账号并填入口令（统一为文档中的演示口令）。管理员账号仅用于管理端，不在 App 登录。
- Android 已通过 Network Security Config 允许默认 HTTP IP 的 cleartext。若自行改为其他 HTTP 地址，需相应增加域名例外，或待服务器启用 HTTPS。

## 本地预览

当前公网 API 若尚未对外，可在登录页选择「本地预览界面」，用内置演示数据走通主要流程（不写真实密码，数据不上传）。界面顶部会标明「本地预览」。

## 构建

要求：Flutter 3.47+（Dart 3.13+）、JDK 17、Android SDK（platforms android-36、build-tools 36）。

```bash
cd /workspace/campus-assistant/app
flutter pub get
flutter analyze
flutter test
flutter build apk --release
# 产物：build/app/outputs/flutter-apk/app-release.apk
# 建议复制到：/workspace/campus-assistant/dist/campus-assistant-v1.apk
```

iOS 请在 macOS 上打开 `ios/Runner.xcworkspace` 构建。本仓库已配置中文显示名、相机/相册权限，以及对 `8.148.186.220` 的 HTTP ATS 例外。

安装包目标为数十 MB，禁止打入大模型或过大资产。

## 主要页面

学生：登录、首页（提问+待办）、对话结果、原文高亮、请假发起/详情/确认、销假确认、奖助草稿确认、报到/作业/志愿者任务、我的档案（含按需授权）、提醒中心（三类可关闭）、我的申请与材料（可复用有效附件）。

教师/辅导员：同样的提问首页，另有发布（作业/招募/报到）、审批箱（批准/退回必填原因/转交）、进度名单。
