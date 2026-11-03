# 报告推送配置

每日 9:00（北京时间）跑完采集与生成后，可以把报告推送到手机或群里。

**不配任何变量时会自动跳过，不影响采集本身。**

## 支持哪些渠道

| 环境变量 | 渠道 | 适用 |
| --- | --- | --- |
| `NOTIFY_PUSHPLUS` + `NOTIFY_PUSHPLUS_CHANNEL=qq` | PushPlus → **QQ 机器人** | 不想折腾微信验证的首选 |
| `NOTIFY_QMSG` + `NOTIFY_QMSG_QQ` | Qmsg酱（QQ 单聊） | 另一条 QQ 路线 |
| `NOTIFY_PUSHPLUS`（channel 默认 wechat） | PushPlus → 微信服务号 | 微信能收到时 |
| `NOTIFY_WECOM` | 企业微信群机器人 | 国内最省事，手机能直接收到 |
| `NOTIFY_BARK` | Bark（iOS App） | iPhone 原生通知 |
| `NOTIFY_DINGTALK` | 钉钉群机器人 | 团队协作 |
| `NOTIFY_FEISHU` | 飞书群机器人 | 团队协作 |
| `NOTIFY_WEBHOOK` | 自定义 webhook | 接自己的服务 |

另外两个可选：

- `NOTIFY_ON_SCHEDULE_ONLY=1`：只在定时任务里推送，手动点「生成」不推
- `NOTIFY_SITE_URL`：报告站点地址，默认 `https://aitrend.lxyblog.top`

## 用 QQ 接收（推荐，绕开微信域名验证）

PushPlus 同时支持 QQ 机器人渠道，**用的还是同一个 token**，只多一个变量。

### 1. 绑定 QQ 机器人

1. 打开 https://www.pushplus.plus → 微信扫码登录
2. 「个人中心」→「**渠道配置**」→ 选「**QQ机器人**」
3. 用 **QQ 扫码**，把机器人加为好友
4. 扫码后没自动绑定的：复制页面上的 6 位绑定码，私聊发给那个机器人

绑定成功后消息直接进 QQ，不需要额外配置。

### 2. EdgeOne 加一个变量

```
NOTIFY_PUSHPLUS_CHANNEL = qq
```

原来的 `NOTIFY_PUSHPLUS`（token）保持不变。两个都在，就走 QQ。

### 3. 两个限制

- QQ 原生 Markdown **不支持代码块和 HTML**，所以 QQ 渠道自动改用纯文本（`template: txt`），链接是纯文本，复制后打开
- QQ 渠道限额：实名用户 **200 次/天**，单条正文上限约 **2000 字**

### 想发到 QQ 群

把机器人拉进群，群设置里**允许机器人主动发言**；再到 PushPlus「QQ机器人 → 新增配置」拿配置编码，
发送时 `option` 填那个编码。当前代码走单聊，要发群再加一个变量。

## 另一条 QQ 路线：Qmsg酱

```
NOTIFY_QMSG     = 你的 key（https://qmsg.zendee.cn 登录后复制）
NOTIFY_QMSG_QQ  = 接收消息的 QQ 号
```

独立的 QQ 推送机器人，扫码登录即可，接口极简。

## 怎么立即测试

不用等第二天。打开站点点「**手动生成**」，跑完就会触发一次推送。

不想手动测试也推，就把 `NOTIFY_ON_SCHEDULE_ONLY` 设为 `1`。

## 怎么排查

EdgeOne 控制台 → 项目 → **函数日志**，搜 `[notify]`：

```
[notify] pushplus-qq:ok
[notify] pushplus-wechat:ok
[notify] errors: [{"channel":"pushplus-qq","ok":false,"detail":"HTTP 200 {\"code\":903...}"}]
```

常见原因：

| 现象 | 原因 |
| --- | --- |
| `code: 905` | PushPlus 没实名，接口被拒 |
| `code: 903` | token 填错 |
| `code: 900/901` | QQ 机器人没绑定，或不在好友列表 |
| 完全没有 `[notify]` 日志 | 环境变量没生效，检查是否重新部署 |

## 关于发到社交平台

微博、小红书、知乎都没有对外开放的发布 API，自动化发帖靠模拟登录，**账号有被封风险**，不建议做。

更稳的做法：

- 报告本身就是网页，分享链接即可
- 加 RSS，别人用 Reeder / Feedly 订阅
- 群里分享，内部传播最快
