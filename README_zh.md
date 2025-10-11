# ComfyDeploy

<div>
  简体中文 / <a href="./README.md">English</a>
</div><br>

ComfyDeploy 是一个 ComfyUI 扩展，允许您配合[comfy-deploy-admin](https://github.com/ihmily/comfy-deploy-admin)将 ComfyUI 工作流部署为 API 服务，并通过外部应用程序轻松调用。

## 功能特点

- 将 ComfyUI 工作流部署为 API 端点
- 支持回调通知
- 支持进度跟踪

## 安装方法

### 方法一：使用 Git

```bash
cd ComfyUI/custom_nodes/
git clone https://github.com/ihmily/comfy-deploy.git
cd comfy-deploy
pip install -r requirements.txt
```

### 方法二：使用ComfyUI-Manager安装

1. 搜索comfy-deploy，选择作者为ihmily的节点
2. 点击安装
3. 重启 ComfyUI

## 完整系统架构

ComfyDeploy 项目系统，由以下两部分组成：

1. **comfy-deploy 节点扩展**（本项目）：安装在 ComfyUI 中的自定义节点，用于创建可部署的工作流。
2. **[comfy-deploy-admin](https://github.com/ihmily/comfy-deploy-admin)**：管理后台系统，用于管理、调试和发布 API 服务。

两个组件协同工作，实现工作流的创建、部署和管理：
- comfy-deploy 节点扩展提供了创建可部署工作流所需的节点和部署功能,将图片、文本等暴露成为外部输入。
- comfy-deploy-admin 提供了管理界面，用于管理已部署的工作流、调试API接口、监控任务执行等

## 使用方法

### 1. 安装 comfy-deploy-admin

请按照 [comfy-deploy-admin 项目](https://github.com/ihmily/comfy-deploy-admin) 的说明安装和配置管理后台：

```bash
git clone https://github.com/ihmily/comfy-deploy-admin.git
cd comfy-deploy-admin
# 按照项目README中的说明继续安装
```

### 2. 配置 ComfyDeploy 节点

在 ComfyUI 界面中，点击顶部菜单栏中的 "ComfyDeploy" 按钮或左侧菜单栏的 "部署" 按钮，配置以下设置：
- API 端点地址：填写 comfy-deploy-admin 的服务地址
- API 密钥：填写在 comfy-deploy-admin 中设置的 API 密钥

### 3. 创建工作流

1. 在您的工作流中添加 ComfyDeploy 节点：
   - External Text (ComfyDeploy)
   - External Integer (ComfyDeploy)
   - External Float (ComfyDeploy)
   - External Image (ComfyDeploy)

2. 为每个节点设置参数名称（param_name），作为外部API请求参数名。

### 4. 部署工作流

1. 创建并测试您的工作流。
2. 点击 "部署" 按钮将工作流部署为 API。
3. 部署成功后到 comfy-deploy-admin 后台查看对应工作流，调试并发布。

## 许可证

[MIT License](LICENSE)
