# 命令与能力索引

命令不必全部对应 skill。命令只是入口，skill 是基础能力或特长能力的调用方式。

## 模式命令

- `/deep-l1`：快速低影响策略，用于快速发现接口、敏感信息和高价值入口。
- `/deep-l2`：默认人工渗透策略，用于理解业务、建立假设、验证权限 / 逻辑 / 数据边界。
- `/deep-l3`：深度白名单策略，用于明确白名单和强度限制后的受控 fuzz、接口猜测和参数猜测。

## 项目命令

- `/src`：初始化正式 SRC / 企业项目声明。
- `/tmp-src`：创建临时项目声明。
- `/update-note`：向当前项目追加补充说明。

## 线索命令

- `/info-find`：给定本地文件或目录，使用正则规则提取 URL、BaseURL、接口路径、参数、认证关键字、敏感配置等线索。
- `/app`：从 APK 中提取接口、参数、配置、客户端逻辑线索。
- `/mapp`：从小程序包中提取接口、页面路由、业务线索。
- `/generate-dict`：根据业务、接口、参数生成低风险字典。

## 沉淀命令

- `/report`：编写或更新报告。
- `/exp`：写入经验库。
- `/specialty-list`：列出可用特长，只检查 `.claude/skills/specialty-skills/`。
- `/specialty-use`：使用某项特长，进入单一挖掘方向。

## 普通 skills

本仓库的普通 skills 位于 `.claude/skills/`，按需读取：

- `project-declaration`：项目声明、默认收录要求、默认注意事项、补充说明。
- `info-find`：给定本地文件或目录，使用正则规则提取 URL、BaseURL、接口路径、参数、认证关键字、敏感配置等信息线索。
- `interface-source`：统一处理 Web / App / 小程序作为接口来源的分析。
- `dict-generator`：低风险路径、参数、备份文件名、业务关键字字典生成。
- `report-writer`：漏洞报告、测试记录、接口清单、未测试危险接口清单。
- `experience-manager`：经验库、踩坑库、指纹与漏洞关联沉淀。

## 特长

普通 skill 不是特长。特长只放在 `.claude/skills/specialty-skills/` 下。

特长是某一种渗透测试思路或挖掘手法。使用特长后，当前阶段只做该特长相关的事情，其他漏洞类型、泛化测试方向和无关信息收集一律不展开。

真实特长目录格式：

- `.claude/skills/specialty-skills/<特长名>/SKILL.md`

`.claude/skills/specialty-skills/SPECIALTY_TEMPLATE.md` 只是特长编写模板，不是真实特长。
