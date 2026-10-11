# 原画差分与纸片动画 Skill

将已有位图角色的表情与局部动作处理固化成可检查的算法工作流：区域归属、供体差分复制、保护区、固定接缝、重心与持物绑定、高清源纹理直接采样，以及配音时间原点与实际输出复核。

本技能总结已验证的技术基础。**不宣称完整影片已通过验收，也不提供已验证的分镜、剧情节奏或场景转场方案。** 具体边界见 [验证范围](skills/cutout-animation/references/validation-scope.md)。

## 使用

将本仓库的 `skills/cutout-animation` 目录复制到你的 Codex 技能目录（通常为 `~/.codex/skills`）。开始新会话后可调用：

> 使用 $cutout-animation，保留我提供的原画，修复闭眼差分和固定部件，先输出原图标记、替换遮罩与像素检查。

技能入口：[SKILL.md](skills/cutout-animation/SKILL.md)。

它是流程与检查工具，不是整套动画渲染器，也不是无需标注的自动拆图。使用自己的基准、供体和标定数据；新视角、新人物、新姿态要重新校准。

## 像素检查

检查工具使用 Python、Pillow、NumPy。在独立 Python 环境安装 `requirements.txt` 后运行：

```text
python skills/cutout-animation/scripts/audit_raster.py replacement --base base.png --candidate blink.png --mask eye-mask.png --protected glasses-mask.png --report checks/blink.json
python skills/cutout-animation/scripts/audit_raster.py assembly --base base.png --layers body.png arm.png --report checks/zero.json
python skills/cutout-animation/scripts/test_audit_raster.py
```

遮罩为同尺寸灰度图，非零表示区域。报告成功为退出码 0，指标失败为 2，输入错误为 1；失败保留差异图。详细说明见 [构建与检查](skills/cutout-animation/references/build-and-check.md)。

## 本次验证

2026-10-11，Python 3.12.14 / NumPy 2.3.5 / Pillow 12.3.0：

- 8 项工具测试通过，覆盖区外变化、保护区变化、alpha 改变、半透明重建、重复部件、透明 RGB 和中文路径诊断。
- 原工程助手的闭眼、闭嘴差分及零动作组合检查通过。
- 技能格式检查通过；所有内部文件链接已检查。
- 原画与认可基准不随技能上传；其认可范围未扩大。

像素检查通过不能证明手部解剖、透视、声音表演或电影剪辑合格。自动指标、人工查看与用户认可分别记录。

仓库仅包含技能说明、可复用检查工具及生成测试，不包含角色原画、录音、影片、浏览器数据或私人邮件。
