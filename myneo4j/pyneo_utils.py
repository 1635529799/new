from py2neo import Graph, Node, Relationship, NodeMatcher, RelationshipMatcher

def get_graph():
    return Graph("bolt://localhost:7687", auth=("neo4j", "123456"), name="neo4j")

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
    print(node_type)
    print(name)
    return matcher.match(node_type, name=name).first()

def get_str_by_dict(mydict):
    last = ""
    for key in mydict:
        last = str(key) + ":" + str(mydict[key]) + "<br>" + last
    return last

# 创建节点和关系
def create_node(start, relation, end, sn, dn):
    g = get_graph()
    print("=========")
    print(sn)
    print(start)

    start_obj = get_node_by_name(g, sn, start)
    if start_obj is None:
        start_obj = Node(sn, name=start)
        g.create(start_obj)

    end_obj = get_node_by_name(g, dn, end)
    if end_obj is None:
        end_obj = Node(dn, name=end)
        g.create(end_obj)

    rel = Relationship(start_obj, relation, end_obj)
    g.create(rel)

    # 返回与 start 节点相关的图谱数据
    return get_all_relation(start, "", "")

def get_all_relation(start, relation, end):
    g = get_graph()

    datas = []
    links = []
    cache = []
    categories = []
    legend_data = []

    # 构建 Cypher 查询
    param = ""
    if start:
        param = f"WHERE n.name='{start}'"
    if relation:
        mr = f"r:{relation}"
    else:
        mr = "r"
    if end:
        param += f" AND b.name='{end}'" if "WHERE" in param else f"WHERE b.name='{end}'"

    sql = f"MATCH (n)-[{mr}]->(b) {param} RETURN n, r, b"
    print(sql)

    nodes_data_all = g.run(sql).data()
    for nodes_relations in nodes_data_all:
        try:
            start_label = str(nodes_relations['n'].labels).replace(":", "")
            end_label = str(nodes_relations['b'].labels).replace(":", "")
            start_dict = dict(nodes_relations['n'])
            end_dict = dict(nodes_relations['b'])

            if "name" not in start_dict or "name" not in end_dict:
                continue

            start_name = start_dict["name"]
            end_name = end_dict["name"]

            try:
                relation_type = str(nodes_relations['r'].keys).split(" ")[4]
            except Exception:
                relation_type = "关联"

            # 处理节点
            if start_name not in cache:
                datas.append({
                    "name": start_name,
                    "attr": start_dict,
                    "color": color.get(start_label, color["other"]),
                    "des": get_str_by_dict(start_dict),
                    "category": start_label
                })
                cache.append(start_name)

            if end_name not in cache:
                datas.append({
                    "name": end_name,
                    "attr": end_dict,
                    "color": color.get(end_label, color["other"]),
                    "des": get_str_by_dict(end_dict),
                    "category": end_label
                })
                cache.append(end_name)

            # 图例分类
            if start_label not in legend_data:
                legend_data.append(start_label)
                categories.append({"name": start_label})
            if end_label not in legend_data:
                legend_data.append(end_label)
                categories.append({"name": end_label})

            # 连线
            rel_key = start_name + "-" + end_name
            if rel_key not in cache:
                links.append({
                    "source": start_name,
                    "target": end_name,
                    "name": relation_type
                })
                cache.append(rel_key)

        except Exception as e:
            print(f"解析失败: {e}")
            continue

    return {
        "datas": datas,
        "links": links,
        "legend_data": legend_data,
        "categories": categories
    }
