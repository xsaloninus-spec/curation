# 策展 (Curation)

HIST2012 课程策展项目总仓库。

## 目录结构

- [`entrance-wall/`](entrance-wall/) — 互动 3D 博物馆入口墙面（React + TypeScript + Vite + Three.js），18 m 连续墙身、8 个展位、90 秒自动导览。详见其 [README](entrance-wall/README.md)。

## 快速开始

```bash
cd entrance-wall
npm install
npm run dev      # 开发服务器
npm run build    # 生产构建（单文件 HTML，输出到 entrance-wall/dist/）
```

## 操作提示

- 空格：暂停 / 继续导览；WASD + 鼠标：自由行走
- `R` 回标题展位，`P` 显示/隐藏标注，`L` 中英切换，`F` 全屏
- 编辑器可修改全部文字分区、导入导出 `wall.json`、为展位导入 GLB 文物模型
