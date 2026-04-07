FROM node:20-alpine

WORKDIR /app

# 使用国内npm镜像源
RUN npm config set registry https://registry.npmmirror.com

# 安装依赖
COPY package.json .
RUN npm install

# 复制代码
COPY . .

# 暴露端口
EXPOSE 5173

# 启动开发服务器
CMD ["npm", "run", "dev"]
