import multiprocessing

# 绑定地址和端口
bind = "0.0.0.0:5001"

# 工作进程数
workers = multiprocessing.cpu_count() * 2 + 1

# 每个worker的最大请求数，防止内存泄漏
max_requests = 1000
max_requests_jitter = 50

# 超时时间
timeout = 30

# 日志配置
accesslog = "-"  # 标准输出
errorlog = "-"   # 标准错误输出

# 防止worker挂掉
preload_app = True

# 优雅重启
graceful_timeout = 30
