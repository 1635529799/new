from py2neo import Graph, Node, Relationship, NodeMatcher, RelationshipMatcher

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
    # g=Graph('http://localhost:7474',user='neo4j',password='123456')
    matcher = NodeMatcher(g)
    endnode = matcher.match(node_type, name=name).first()
    print(endnode)
    if endnode != None:
        return endnode
    else:
        return None


def get_str_by_dict(mydict):
    last = ""
    print(mydict)
    print(type(mydict))
    for key in mydict:
        last = str(key) + ":" + str(mydict[key]) + "<br>" + last
    return last



