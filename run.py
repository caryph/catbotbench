from handler import request

ans, cost = request("tell me about discord cat bot", "poolside/laguna-s-2.1:free", True)
print(ans)