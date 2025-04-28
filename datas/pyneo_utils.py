from py2neo import Graph, Node, Relationship, NodeMatcher


def get_graph():
    """
    统一图数据库连接方式
    """
    return Graph("bolt://localhost:7687", auth=("neo4j", "123456"))


color = {
    "CLASS": "#5470c6",
    "TIME": "#e474c6",
    "LOC": "#147fc6",
    "RES": "#947dc6",
    "EVE": "#847986",
    "EVC": "#8374r6",
    "other": "#111111"
}


def get_node_by_name(g, node_type, name):
    matcher = NodeMatcher(g)
    endnode = matcher.match(node_type, name=name).first()
    print(f"查询节点: {node_type} -> {name}，结果: {endnode}")
    return endnode


def get_str_by_dict(mydict):
    """
    将字典转为 HTML 显示格式字符串
    """
    result = ""
    for key in mydict:
        result = f"{key}:{mydict[key]}<br>" + result
    return result


def get_all_relation(start, relation, end):
    """
    查询图谱中某个节点及其相关的所有关系数据
    返回格式：用于可视化图谱展示的结构
    """
    g = get_graph()
    datas, links, cache = [], [], []
    categories, legend_data = [], []

    # 构造 Cypher 查询
    cypher = "MATCH (n)-[%s]->(b) %s RETURN n, r, b"
    where_clause = []
    rel_type = "r" if not relation else f"r:{relation}"

    if start:
        where_clause.append(f"n.name='{start}'")
    if end:
        where_clause.append(f"b.name='{end}'")

    where_clause = "WHERE " + " AND ".join(where_clause) if where_clause else ""
    cypher = cypher % (rel_type, where_clause)
    print(f"执行 Cypher：{cypher}")

    result = g.run(cypher).data()

    for item in result:
        node_n, node_b = dict(item["n"]), dict(item["b"])
        rel = item["r"]

        start_label = list(item["n"].labels)[0] if item["n"].labels else "unknown"
        end_label = list(item["b"].labels)[0] if item["b"].labels else "unknown"
        start_name = node_n.get("name")
        end_name = node_b.get("name")
        rel_name = rel.__class__.__name__

        if not start_name or not end_name:
            continue

        if start_name not in cache:
            datas.append({
                "name": start_name,
                "attr": node_n,
                "color": color.get(start_label, color["other"]),
                "des": get_str_by_dict(node_n),
                "category": start_label
            })
            cache.append(start_name)

        if end_name not in cache:
            datas.append({
                "name": end_name,
                "attr": node_b,
                "color": color.get(end_label, color["other"]),
                "des": get_str_by_dict(node_b),
                "category": end_label
            })
            cache.append(end_name)

        link_id = f"{start_name}-{end_name}"
        if link_id not in cache:
            links.append({
                "source": start_name,
                "target": end_name,
                "name": rel_name
            })
            cache.append(link_id)

        if start_label not in legend_data:
            legend_data.append(start_label)
            categories.append({"name": start_label})
        if end_label not in legend_data:
            legend_data.append(end_label)
            categories.append({"name": end_label})

    return {
        "datas": datas,
        "links": links,
        "legend_data": legend_data,
        "categories": categories
    }