# distribution: 同事试用分发

## 意图

让使用不同本机路径的同事能够安全安装和检查 SMM。

## 外部行为

### distribution-1

当用户从发行目录安装 SMM 时，系统应建立可运行环境并将同一 Skill 与 MCP 服务注册到本机已安装的 Codex 和 Claude Code。

### distribution-2

当用户重复安装相同版本时，系统应保留已有档案和用户设置，且不产生重复配置。

### distribution-3

当用户运行诊断时，系统应报告来源目录、数据库、服务、Skill、MCP 注册与导入状态，并明确区分本机接入检查与模型登录状态。

### distribution-4

当用户从另一绝对路径重新安装时，系统应更新其拥有的入口以指向新位置，且 Skill 不依赖开发者个人路径。

### distribution-5

当用户卸载 SMM 入口时，系统应停用服务并移除其拥有的 Skill 与 MCP 配置，同时保留已导入档案。

### distribution-6

当用户获取试用发行包时，发行包应只包含程序与说明，不包含用户对话、数据库或凭证。

## 验证

### distribution-7

在干净用户目录安装、重复安装、搬迁安装、诊断与卸载时，应分别验证 [[distribution-1](#distribution-1)]、[[distribution-2](#distribution-2)]、[[distribution-3](#distribution-3)]、[[distribution-4](#distribution-4)] 与 [[distribution-5](#distribution-5)]。

### distribution-8

在封存发行包时，应核对文件清单与凭证扫描以验证 [[distribution-6](#distribution-6)]。
