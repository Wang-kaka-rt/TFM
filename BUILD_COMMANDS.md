# 依赖安装与构建命令

## 1) Node 桥接服务（NestJS）

```bash
cd code/node
npm install
npm run build
```

## 2) Python 服务

```bash
cd code/python
py -m pip install -r requirements.txt
```

## 3) Python 打包构建 EXE

```bash
cd code/python
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

## 4) Strudel 前端（可选）

```bash
cd code/strudel-src-real
pnpm i
npm run build
```
