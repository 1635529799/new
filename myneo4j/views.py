from django.shortcuts import render, HttpResponse, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.conf import settings
from openai import OpenAI
from py2neo import Graph

from myneo4j.pyneo_utils import get_graph
from myneo4j.utils import get_datas, get_entitys, service_upload, get_answers
from myneo4j.ner_utils import posseg_key
from datas.entity_dict import get_ents, embs
from .LLM import *
from .models import MyNode, MyWenda, Question
import time
import sys
import uuid
import os
import json
import pdfplumber
from io import BytesIO
from threading import Thread

from .pyneo_utils import get_all_relation

progress_state = {}
extraction_results = {}
client = OpenAI(
    api_key="sk-7ca946c7053e4a5a8d3849f7659bc80a",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)
list_embs = embs()
ku_qs = get_ents()

@login_required
def index(request):
    try:
        start = request.GET.get("key", "") or "防护用品"
        inputs = start
        ssss = request.session.get('ac', "") == True
        relation = request.GET.get("relation", "")
        end = request.GET.get("end", "")
        all_datas = get_all_relation(start, relation, end)
        links = json.dumps(all_datas["links"])
        datas = json.dumps(all_datas["datas"])
        categories = json.dumps(all_datas["categories"])
        legend_data = json.dumps(all_datas["legend_data"])
        s_dict = all_datas["datas"][0]['attr']
    except Exception as e:
        print(e)
    return render(request, "index.html", locals())

from py2neo import Graph

@login_required
@login_required
def get_all_nodes(request):
    g = get_graph()

    # 获取查询参数
    graph_name = request.GET.get('graph', '')
    query = request.GET.get('key', '')

    # 构造基本Cypher条件
    where_clauses = []

    if graph_name:
        where_clauses.append(f"n:{graph_name} AND m:{graph_name}")
    if query:
        # 搜索节点名称或关系类型
        where_clauses.append(f"(n.name CONTAINS '{query}' OR type(r) CONTAINS '{query}' OR m.name CONTAINS '{query}')")

    where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    # 先查询总数
    count_cypher = f"""
    MATCH (n)-[r]->(m)
    {where_clause}
    RETURN count(r) AS total
    """
    total_records = g.run(count_cypher).evaluate() or 0

    # 分页参数
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))
    skip_count = (page - 1) * page_size

    # 查询当前页的数据
    cypher = f"""
    MATCH (n)-[r]->(m)
    {where_clause}
    RETURN n, r, m
    SKIP {skip_count}
    LIMIT {page_size}
    """
    nodes_data = g.run(cypher).data()

    # 查询所有图谱名
    graphs_query = g.run("CALL db.labels()").data()
    graphs = [record['label'] for record in graphs_query]

    # 格式化
    formatted_nodes = [
        {
            'start_node': record['n']['name'],
            'start_node_type': list(record['n'].labels)[0],
            'relationship': type(record['r']).__name__,
            'end_node': record['m']['name'],
            'end_node_type': list(record['m'].labels)[0],
        }
        for record in nodes_data
    ]

    return render(request, 'admin.html', {
        'nodes': formatted_nodes,
        'page': page,
        'total_pages': (total_records + page_size - 1) // page_size,
        'page_size': page_size,
        'total_count': total_records,
        'graphs': graphs,
        'selected_graph': graph_name,
        'query': query,
    })



@login_required
def delete_relationship_view(request):
    if request.method == 'POST':
        g = get_graph()
        start_node = request.POST.get('start_node')
        end_node = request.POST.get('end_node')
        relationship = request.POST.get('relationship')

        try:
            cypher_query = f"""
                MATCH (n)-[r:{relationship}]->(m)
                WHERE n.name = '{start_node}' AND m.name = '{end_node}'
                DELETE r
            """
            g.run(cypher_query)
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

@login_required
def add(request):
    if request.method == 'GET':
        return render(request, "add.html", locals())

    if request.method == 'POST':
        g = get_graph()
        start_node = request.POST.get('start_node')
        start_node_type = request.POST.get('start_node_type')
        end_node = request.POST.get('end_node')
        relationship = request.POST.get('relationship')
        end_node_type = request.POST.get('end_node_type')

        g.run(f"MERGE (a:{start_node_type} {{name: '{start_node}'}})")
        g.run(f"MERGE (b:{end_node_type} {{name: '{end_node}'}})")
        g.run(f"""
            MATCH (a:{start_node_type} {{name: '{start_node}'}}), 
                  (b:{end_node_type} {{name: '{end_node}'}})
            CREATE (a)-[:{relationship}]->(b)
        """)
        return redirect('/get_all')

@login_required
def edit(request):
    if request.method == 'GET':
        g = get_graph()
        start_node = request.GET.get('start_node')
        start_node_type = request.GET.get('start_node_type')
        relationship = request.GET.get('relationship')
        end_node = request.GET.get('end_node')
        end_node_type = request.GET.get('end_node_type')
        cypher_query = f"""
            MATCH (n)-[r:{relationship}]->(m)
            WHERE n.name = '{start_node}' AND m.name = '{end_node}'
            DELETE r
        """
        g.run(cypher_query)

    if request.method == 'POST':
        g = get_graph()
        start_node = request.POST.get('start_node')
        start_node_type = request.POST.get('start_node_type')
        end_node = request.POST.get('end_node')
        relationship = request.POST.get('relationship')
        end_node_type = request.POST.get('end_node_type')

        g.run(f"MERGE (a:{start_node_type} {{name: '{start_node}'}})")
        g.run(f"MERGE (b:{end_node_type} {{name: '{end_node}'}})")
        g.run(f"""
            MATCH (a:{start_node_type} {{name: '{start_node}'}}), 
                  (b:{end_node_type} {{name: '{end_node}'}})
            CREATE (a)-[:{relationship}]->(b)
        """)
        return redirect('/get_all')

    return render(request, "edit.html", locals())

@login_required
def rec(request):
    start = request.GET.get("key", "")
    relation = request.GET.get("relation", "")
    end = request.GET.get("end", "")

    result = posseg_key(start, './datas/entitys.txt')
    entity = result[0] if result else get_entitys(start, client, list_embs, ku_qs)

    all_datas = get_all_relation(entity, relation, end) if entity else None

    links = json.dumps(all_datas["links"]) if all_datas else "[]"
    datas = json.dumps(all_datas["datas"]) if all_datas else "[]"
    categories = json.dumps(all_datas["categories"]) if all_datas else "[]"
    legend_data = json.dumps(all_datas["legend_data"]) if all_datas else "[]"

    return render(request, "index.html", locals())

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

import contextlib

import os

@csrf_exempt
@login_required
def get_progress(request):
    user_id = str(request.user.id)
    current_state = progress_state.get(user_id, "⌛ 等待开始...")

    # 静音打印，只影响当前请求
    with open(os.devnull, 'w') as fnull:
        with contextlib.redirect_stdout(fnull):
            return JsonResponse({'state': current_state})




@csrf_exempt
@login_required
def upload_html(request):
    user_id = str(request.user.id)

    if request.method == 'POST':
        try:
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                progress_state[user_id] = "❌ 上传失败：未选择文件"
                return JsonResponse({'status': 'error', 'message': '未选择文件'})

            ext = os.path.splitext(uploaded_file.name)[1]  # 获取真实后缀
            if ext.lower() not in ['.pdf', '.txt']:
                progress_state[user_id] = "❌ 上传失败：仅支持 PDF 或 TXT 文件"
                return JsonResponse({'status': 'error', 'message': '仅支持 PDF 或 TXT 文件'})

            filename = f"{uuid.uuid4()}{ext}"
            upload_path = os.path.join(settings.BASE_DIR, 'uploads')
            os.makedirs(upload_path, exist_ok=True)
            file_path = os.path.join(upload_path, filename)

            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            progress_state[user_id] = "📄 上传成功"
            Thread(target=extract_and_upload_from_file, args=(user_id, file_path, uploaded_file.name)).start()

            return JsonResponse({'status': 'success', 'message': '正在后台抽取中...'})

        except Exception as e:
            progress_state[user_id] = "❌ 抽取失败"
            return JsonResponse({'status': 'error', 'message': str(e)})

    return render(request, "up1.html", locals())

@csrf_exempt
@login_required
def node_detail(request):
    g = get_graph()

    node_name = request.GET.get('name')
    if not node_name:
        return JsonResponse({'error': '缺少参数'}, status=400)

    try:
        # 查找这个节点及其相关关系
        query = f"""
        MATCH (n)-[r]->(m)
        WHERE n.name = '{node_name}'
        RETURN n, r, m
        UNION
        MATCH (n)<-[r]-(m)
        WHERE n.name = '{node_name}'
        RETURN n, r, m
        """
        data = g.run(query).data()

        nodes = []
        links = []
        node_names = set()

        for record in data:
            start_node = record['n']
            end_node = record['m']
            rel = record['r']

            if start_node['name'] not in node_names:
                nodes.append({'name': start_node['name'], 'category': list(start_node.labels)[0]})
                node_names.add(start_node['name'])
            if end_node['name'] not in node_names:
                nodes.append({'name': end_node['name'], 'category': list(end_node.labels)[0]})
                node_names.add(end_node['name'])

            links.append({
                'source': start_node['name'],
                'target': end_node['name'],
                'name': type(rel).__name__,
                'text': rel.get('text', '')  # 取原文片段
            })

        # ✅ 一定要转成JSON字符串
        return render(request, 'node_detail.html', {
            'node_name': node_name,
            'nodes': json.dumps(nodes, ensure_ascii=False),
            'links': json.dumps(links, ensure_ascii=False),
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def extract_and_upload_from_file(user_id, file_path, original_name):
    try:
        progress_state[user_id] = "✂️ 正在抽取三元组"

        text_content = ""
        if file_path.lower().endswith('.pdf'):
            with pdfplumber.open(file_path) as pdf:
                text_content = "\n".join(
                    page.extract_text() if isinstance(page.extract_text(), str) else ""
                    for page in pdf.pages
                )
        elif file_path.lower().endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
        else:
            progress_state[user_id] = "❌ 抽取失败：不支持的文件格式"
            return

        if not text_content.strip():
            progress_state[user_id] = "❌ 抽取失败：文本内容为空"
            return

        df = get_triples(client, text_content, original_name)
        if df is None:
            progress_state[user_id] = "❌ 抽取失败：未返回三元组"
            return

        progress_state[user_id] = "🧠 正在写入图谱"

        service_upload(df, client)  # ⚡写入数据库，这里很可能会耗时

        # 加一小段确认等待
        time.sleep(0.5)  # 小等0.5秒，确保后端刷完缓存
        #  保存提取出来的三元组列表
        extraction_results[user_id] = df.to_dict(orient='records')

        # 再更新进度
        progress_state[user_id] = "✅ 抽取流程完成"

    except Exception as e:
        progress_state[user_id] = f"❌ 抽取失败：{str(e)}"
    finally:
        os.remove(file_path)


from django.contrib.auth.decorators import login_required



@csrf_exempt
@login_required
def chat(request):
    try:
        g = get_graph()
        user = request.user
        all_wendas = MyWenda.objects.filter(user=user).order_by("-id")[:20][::-1]


        if request.method == "GET":
            key = request.GET.get("key", "")
            clean = request.GET.get("clean", "")

            if clean:
                MyWenda.objects.filter(user=user).delete()
                all_wendas = []  # ✅ 清空变量，避免残留

            if key:
                flag = True
                entity = ""
                result = posseg_key(key, './datas/entitys.txt')
                if result:
                    entity = result[0]
                elif get_entitys(key, client, list_embs, ku_qs) and not entity:
                    entity = get_entitys(key, client, list_embs, ku_qs)
                    flag = False

                all_datas = get_all_relation(entity, "", "") if entity else None
                daan, text = get_answers(entity, flag, client, key, g)

                if all_datas:
                    links = json.dumps(all_datas["links"])
                    datas = json.dumps(all_datas["datas"])
                    categories = json.dumps(all_datas["categories"])
                    legend_data = json.dumps(all_datas["legend_data"])

                MyWenda.objects.filter(user=user, question=key, anster=daan).delete()
                MyWenda.objects.create(user=user, question=key, anster=daan)

                all_wendas = MyWenda.objects.filter(user=user).order_by("id")[:10]  # ✅ 再次刷新历史

        return render(request, "chat1.html", locals())

    except Exception as e:
        print("chat view error:", e)
        return render(request, "chat1.html", locals())

@csrf_exempt
@login_required
def get_extraction_result(request):
    user_id = str(request.user.id)
    result = extraction_results.get(user_id, [])
    return JsonResponse({'data': result})
