from django.shortcuts import render, HttpResponse
import os
import time
import json
from openai import OpenAI
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect,get_object_or_404
from .pyneo_utils import *
from django.views.decorators.csrf import csrf_exempt
from myneo4j.utils import get_datas,get_entitys,service_upload,get_answers
from myneo4j.ner_utils import posseg_key
from django.http import JsonResponse,HttpResponse
from django.core.paginator import Paginator
from datas.entity_dict import get_ents,embs
from .LLM import *
import PyPDF2
import pdfplumber
from io import BytesIO
from .models import MyNode, MyWenda,Question

# 初始化 API 客户端
client = OpenAI(
    api_key="sk-7ca946c7053e4a5a8d3849f7659bc80a",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)
list_embs=embs()
ku_qs=get_ents()



@login_required
def index(request):
    try:
        start = request.GET.get("key", "")
        if start=="":
            start="防护用品"
        inputs=start
        if request.session.get('ac',"")==True:
            ssss=True
        else:
            ssss=False
        relation = request.GET.get("relation", "")
        end = request.GET.get("end", "")
        all_datas = get_all_relation(start, relation, end)
        links = json.dumps(all_datas["links"])
        datas = json.dumps(all_datas["datas"])
        categories = json.dumps(all_datas["categories"])
        legend_data = json.dumps(all_datas["legend_data"])
        s_dict= all_datas["datas"][0]['attr']


    except Exception as e:
        print(e)
    return render(request, "index.html", locals())


@login_required
def get_all_nodes(request):
    query = request.GET.get('key', '')

    # g = Graph('http://localhost:7474', user='neo4j', password='123456')

    # 基本查询语句，支持查询节点名称或关系
    if query:
        sql = f"MATCH (n)-[r]->(m) WHERE n.name CONTAINS '{query}' OR type(r) CONTAINS '{query}' RETURN n, r, m limit 100"
    else:
        sql = "MATCH (n)-[r]->(m) RETURN n, r, m limit 100"

    # 执行查询
    nodes_data_all = g.run(sql).data()

    # 处理分页
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 10)
    paginator = Paginator(nodes_data_all, page_size)
    nodes = paginator.get_page(page)

    # 格式化结果
    formatted_nodes = []
    for record in nodes:
        formatted_nodes.append({
            'start_node': record['n']['name'],
            'start_node_type': list(record['n'].labels)[0],
            'relationship': type(record['r']).__name__,
            'end_node': record['m']['name'],
            'end_node_type': list(record['m'].labels)[0],
        })

    # 传递数据到模板
    return render(request, 'admin.html', {
        'nodes': formatted_nodes,
        'page': nodes.number,
        'total_pages': paginator.num_pages,
        'page_size': page_size,
        'total_count': paginator.count,
        'query': query,  # 将查询条件传回前端
    })

@login_required
def delete_relationship_view(request):
    if request.method == 'POST':
        # 获取表单提交的数据
        start_node = request.POST.get('start_node')
        end_node = request.POST.get('end_node')
        relationship = request.POST.get('relationship')

        # 连接到 Neo4j
        # g = Graph('http://localhost:7474', user='neo4j', password='123456')

        try:
            # 构建 Cypher 查询，删除关系
            cypher_query = f"""
            MATCH (n)-[r:{relationship}]->(m)
            WHERE n.name = '{start_node}' AND m.name = '{end_node}'
            DELETE r
            """
            print(cypher_query)
            g.run(cypher_query)

            # 返回成功响应
            return JsonResponse({'success': True})
        except Exception as e:
            print(e)
            return JsonResponse({'success': False, 'error': str(e)})
@login_required
def add(request):
    if request.method == 'GET':
        return render(request, "add.html", locals())
    if request.method == 'POST':
        start_node = request.POST.get('start_node')
        start_node_type = request.POST.get('start_node_type')
        end_node = request.POST.get('end_node')
        relationship = request.POST.get('relationship')
        end_node_type = request.POST.get('end_node_type')
        print(start_node)
        # g = Graph('http://localhost:7474', user='neo4j', password='123456')

        g.run(f"""
                   MERGE (a:{start_node_type} {{name: '{start_node}'}})
                   """)
        g.run(f"""
                   MERGE (b:{end_node_type} {{name: '{end_node}'}})
                   """)
        # 创建关系
        g.run(f"""
                   MATCH (a:{start_node_type} {{name: '{start_node}'}}), (b:{end_node_type} {{name: '{end_node}'}})
                   CREATE (a)-[:{relationship}]->(b)
                   """)

        print(f"成功新增节点和关系：{relationship} 从 {start_node} 到 {end_node}")

        return redirect('/get_all')



@login_required
def edit(request):
    if request.method == 'GET':
        # g = Graph('http://localhost:7474', user='neo4j', password='123456')
        # end_node_type={{record.end_node_type}}
        start_node = request.GET.get('start_node')
        start_node_type = request.GET.get('start_node_type')
        relationship = request.GET.get('relationship')
        end_node= request.GET.get('end_node')
        end_node_type = request.GET.get('end_node_type')
        cypher_query = f"""
                    MATCH (n)-[r:{relationship}]->(m)
                    WHERE n.name = '{start_node}' AND m.name = '{end_node}'
                    DELETE r
                    """
        print(cypher_query)
        g.run(cypher_query)

    if request.method == 'POST':
        start_node = request.POST.get('start_node')
        start_node_type = request.POST.get('start_node_type')
        end_node = request.POST.get('end_node')
        relationship = request.POST.get('relationship')
        end_node_type = request.POST.get('end_node_type')
        print(start_node)
        # g = Graph('http://localhost:7474', user='neo4j', password='123456')

        g.run(f"""
                   MERGE (a:{start_node_type} {{name: '{start_node}'}})
                   """)
        g.run(f"""
                   MERGE (b:{end_node_type} {{name: '{end_node}'}})
                   """)
        # 创建关系
        g.run(f"""
                   MATCH (a:{start_node_type} {{name: '{start_node}'}}), (b:{end_node_type} {{name: '{end_node}'}})
                   CREATE (a)-[:{relationship}]->(b)
                   """)

        print(f"成功新增节点和关系：{relationship} 从 {start_node} 到 {end_node}")

        return redirect('/get_all')

    return render(request, "edit.html", locals())

@login_required
def rec(request):
    start = request.GET.get("key", "")
    inputs = start
    relation = request.GET.get("relation", "")
    if request.session.get('ac', "") == True:
        ssss = True
    else:
        ssss = False

    end = request.GET.get("end", "")
    key = ""
    result = posseg_key(start, './datas/entitys.txt')
    entity=""
    if len(result) > 0:
        entity = result[0]
    elif get_entitys(start, client, list_embs, ku_qs) != '' and entity == "" and start!="":
        entity = get_entitys(start, client, list_embs, ku_qs)  # 实体扩充
    else:
        entity = ""
    en = entity
    all_datas = get_all_relation(en, relation, end)
    links = json.dumps(all_datas["links"])
    datas = json.dumps(all_datas["datas"])
    categories = json.dumps(all_datas["categories"])
    legend_data = json.dumps(all_datas["legend_data"])


    return render(request, "index.html", locals())
# @login_required
# def wenda_html(request):
#     return render(request, "chat.html", locals())
@csrf_exempt
@login_required
def upload_html(request):
    if request.method == 'POST':
        # 获取上传文件
        uploaded_file = request.FILES.get('file')

        if not uploaded_file:
            return JsonResponse({'status': 'error', 'message': '未选择文件'})

        # 文件类型验证
        if not (uploaded_file.content_type == 'application/pdf' and
                uploaded_file.name.lower().endswith('.pdf')):
            return JsonResponse({'status': 'error', 'message': '仅支持PDF格式'})
        try:
        # if True:
            # ========== 内存中处理文件 ==========
            file_content = uploaded_file.read()
            with pdfplumber.open(BytesIO(file_content)) as pdf:
                text_content = "\n".join(page.extract_text() for page in pdf.pages)
            df=get_triples(client, text_content, uploaded_file.name)
            if df is None:
                return JsonResponse({'status': 'success', 'message': '数据错误！'})
            else:
                service_upload(df,client)
            return JsonResponse({'status': 'success', 'message': '实体关系抽取成功！'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'实体关系抽取失败: {str(e)}'})

    return render(request, "up1.html", locals())



# @csrf_exempt
# def chat(request):
#
#     try:
#         if request.method == "POST":
#             key = request.POST.get("prompts", None)
#             if key:
#                 # json串转对象
#                 flag=True
#                 prompts = json.loads(key)
#                 key=prompts[-1]['content']
#                 print(key)
#                 entity=""
#                 result = posseg_key(key, './datas/entitys.txt')
#                 if len(result) > 0:
#                     entity = result[0]
#                     print(key)
#                     print('================')
#                 elif get_entitys(key,client,list_embs ,ku_qs) != '' and  entity == "":
#                     entity= get_entitys(key,client,list_embs , ku_qs)  # 实体扩充
#                     flag=False
#                 else:
#                     entity=""
#
#                 daan = ""
#                 # g = Graph('http://localhost:7474', user='neo4j', password='123456')
#                 if (entity!="")&(entity!=None):
#                     sql = "MATCH (n)-[r]->(b) where n.name='%s' RETURN r,b" % (entity)
#                     # print(sql)
#                     nodes_data_all = g.run(sql).data()
#                     mnjh = ""
#                     mn=""
#                     if len(nodes_data_all) > 0:
#                         for nodes_relations in nodes_data_all:
#                             node_dict = dict(nodes_relations['b'])
#                             mnjh = mnjh+node_dict["text"] + "；"
#                             r = str(nodes_relations['r']).split(":")[1].split("{")[0].strip()
#                             mn = mnjh + r + ":" + node_dict["name"] + " "
#                     daan=mn+mnjh
#                     if (flag != True) :
#                         key = key + "注意：问题中进行了实体扩充，更正，用扩充和更正的实体回答，正确的实体是：" + entity
#                 else:
#                     daan = "暂时不支持此类问题，可以试试问：实体+关系问答模式(例如：土壤理化特性包含的特性指标有那些？)"
#
#                 daan = get_answer(client, key, daan, "deepseek-v3")
#                 return HttpResponse(daan, content_type='application/octet-stream')
#             else:
#                 return JsonResponse({"error": {"message": "请输入内容！", "type": "invalid_request_error", "code": ""}})
#
#     except Exception as e:
#
#         return JsonResponse({"error": {"message": "请求超时，请稍后再试！", "type": "timeout_error", "code": ""}})

@csrf_exempt
@login_required
def chat(request):
    try:
        user = request.user

        if request.method == "GET":
            key = request.GET.get("key", "")
            clean = request.GET.get("clean", "")
            if clean:
                all_wendas111 = MyWenda.objects.filter(user=user).order_by("id")
                print(all_wendas111)
                for js in all_wendas111:
                    js.delete()
            flag=True
            if key:
                entity=""
                result = posseg_key(key, './datas/entitys.txt')
                if len(result) > 0:
                        entity = result[0]
                elif get_entitys(key,client,list_embs ,ku_qs) != '' and  entity == "":
                        entity= get_entitys(key,client,list_embs , ku_qs)  # 实体扩充
                        flag=False
                else:
                        entity=""
                if (entity != "") & (entity != None):
                    sen=entity
                    all_datas = get_all_relation(entity, "", "")
                else:
                    all_datas = None
                daan,text=get_answers(entity,flag,client,key,g)

                if all_datas != None:
                    links = json.dumps(all_datas["links"])
                    datas = json.dumps(all_datas["datas"])
                    categories = json.dumps(all_datas["categories"])
                    legend_data = json.dumps(all_datas["legend_data"])


                wenda = MyWenda.objects.filter(user=user, question=key, anster=daan)
                if len(wenda) > 0:
                        for w in wenda:
                            w.delete()
                wenda = MyWenda()
                wenda.user = user
                wenda.question = key
                wenda.anster = daan
                wenda.save()

            all_wendas = MyWenda.objects.filter(user=user).order_by("id")[:10]

            return render(request, "chat1.html", locals())
    except Exception as e:
        print(e)
        return render(request, "chat1.html", locals())