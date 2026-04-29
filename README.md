# 依赖安装、启动与构建命令

## 1) Node 桥接服务（NestJS）

### 安装依赖
```bash
cd code/node
npm install
```

### 启动（开发）
```bash
cd code/node
npm run start:dev
```

### 构建
```bash
cd code/node
npm run build
```

## 2) Python 后端服务

### 安装依赖
```bash
cd code/python
py -m pip install -r requirements.txt
```

### 启动（开发）
```bash
cd code/python
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

### 构建（打包 EXE）
```bash
cd code/python
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

## 3) Strudel 前端（可选）

### 安装依赖
```bash
cd code/strudel-src-real
pnpm i
```

### 启动（开发）
```bash
cd code/strudel-src-real
npm run dev
```

### 构建
```bash
cd code/strudel-src-real
npm run build
```
