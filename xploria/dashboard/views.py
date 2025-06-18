import sqlite3
import pandas as pd
import altair as alt
from django.shortcuts import render
import json
from django.http import JsonResponse

DB_PATH = "data.db"

def get_connection():
    try:
        return sqlite3.connect(DB_PATH)
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def home(request):
    return render(request, 'dashboard/home.html')

def tables(request):
    conn = get_connection()
    tables = []
    table_data = None
    selected_table = None
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        
        if 'table' in request.GET:
            selected_table = request.GET['table']
            try:
                df = pd.read_sql_query(f"SELECT * FROM `{selected_table}` LIMIT 100", conn)
                table_data = df.to_html(index=False, classes='custom-table')
            except Exception as e:
                table_data = f"<div class='alert alert-danger'>Error: {str(e)}</div>"
    
    context = {
        'tables': tables,
        'selected_table': selected_table,
        'table_data': table_data
    }
    return render(request, 'dashboard/tables.html', context)

def query_editor(request):
    query_result = None
    query_input = ""
    
    if request.method == 'POST':
        query_input = request.POST.get('query', '')
        if query_input.strip():
            conn = get_connection()
            if conn:
                try:
                    df = pd.read_sql_query(query_input, conn)
                    query_result = df.to_html(index=False, classes='custom-table')
                except Exception as e:
                    try:
                        cursor = conn.cursor()
                        cursor.execute(query_input)
                        conn.commit()
                        query_result = "<div class='alert alert-success'>Query executed successfully (no result set)</div>"
                    except Exception as inner_e:
                        query_result = f"<div class='alert alert-danger'>Error: {str(inner_e)}</div>"
    
    context = {
        'query_input': query_input,
        'query_result': query_result
    }
    return render(request, 'dashboard/query_editor.html', context)

def designer(request):
    conn = get_connection()
    tables = []
    create_result = None
    insert_result = None
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        
        # Create Table Logic
        if request.method == 'POST' and 'create_table' in request.POST:
            table_name = request.POST.get('table_name', '')
            columns_input = request.POST.get('columns_input', '')
            if table_name and columns_input:
                try:
                    cursor.execute(f"CREATE TABLE {table_name} ({columns_input})")
                    conn.commit()
                    create_result = f"<div class='alert alert-success'>Table '{table_name}' created successfully</div>"
                    # Refresh tables list
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [t[0] for t in cursor.fetchall()]
                except Exception as e:
                    create_result = f"<div class='alert alert-danger'>Error: {str(e)}</div>"
        
        # Insert Data Logic
        if request.method == 'POST' and 'insert_record' in request.POST:
            selected_table = request.POST.get('selected_table', '')
            if selected_table:
                try:
                    cursor.execute(f"PRAGMA table_info({selected_table})")
                    columns_info = cursor.fetchall()
                    values = []
                    for col in columns_info:
                        val = request.POST.get(f"col_{col[1]}", '')
                        values.append(val)
                    
                    placeholders = ", ".join(["?"] * len(values))
                    col_names = ", ".join([col[1] for col in columns_info])
                    cursor.execute(f"INSERT INTO {selected_table} ({col_names}) VALUES ({placeholders})", values)
                    conn.commit()
                    insert_result = "<div class='alert alert-success'>Record inserted successfully</div>"
                except Exception as e:
                    insert_result = f"<div class='alert alert-danger'>Error: {str(e)}</div>"
    
    context = {
        'tables': tables,
        'create_result': create_result,
        'insert_result': insert_result
    }
    return render(request, 'dashboard/designer.html', context)

def analytics(request):
    conn = get_connection()
    table_data = None
    chart1 = None
    chart2 = None
    
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [t[0] for t in cursor.fetchall()]
            row_counts = []
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    row_counts.append(count)
                except:
                    row_counts.append(0)
            
            df_summary = pd.DataFrame({
                "Table": tables,
                "Rows": row_counts
            }).sort_values(by="Rows", ascending=False)
            
            table_data = df_summary.to_html(index=False, classes='custom-table')
            
            # Chart 1: Row count per table
            if not df_summary.empty:
                chart1 = alt.Chart(df_summary).mark_bar(
                    color="#14655B"
                ).encode(
                    x=alt.X('Table:N', sort='-y', title='Table'),
                    y=alt.Y('Rows:Q', title='Row Count'),
                    tooltip=['Table', 'Rows']
                ).properties(
                    height=300,
                    width=500
                ).to_json()
            
            # Chart 2: Tools by Rating
            try:
                rating_df = pd.read_sql("""
                    SELECT rating_stars, COUNT(*) as count
                    FROM CategoryAI
                    GROUP BY rating_stars
                """, conn)
                
                if not rating_df.empty:
                    chart2 = alt.Chart(rating_df).mark_bar(
                        color="#14655B"
                    ).encode(
                        x=alt.X('rating_stars:N', title='Rating'),
                        y=alt.Y('count:Q', title='Count'),
                        tooltip=['rating_stars', 'count']
                    ).properties(
                        height=300,
                        width=500
                    ).to_json()
            except Exception as e:
                print(f"Rating chart error: {str(e)}")
        except Exception as e:
            print(f"Analytics error: {str(e)}")
    
    context = {
        'table_data': table_data,
        'chart1': chart1,
        'chart2': chart2
    }
    return render(request, 'dashboard/analytics.html', context)

def get_columns(request):
    table = request.GET.get('table')
    if not table:
        return JsonResponse({'error': 'Table name not provided'}, status=400)

    conn = get_connection()
    if not conn:
        return JsonResponse({'error': 'Database connection error'}, status=500)
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        columns_info = cursor.fetchall()

        columns = []
        for col in columns_info:
            columns.append({
                'name': col[1],
                'type': col[2]
            })

        return JsonResponse({'columns': columns})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)