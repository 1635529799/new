from py2neo import Graph

try:
    g = Graph("bolt://localhost:7687", auth=("neo4j", "123456"))  # 不加 name 参数
    result = g.run("RETURN '连接成功' AS message").data()
    print(result)
except Exception as e:
    print("连接失败：", e)
