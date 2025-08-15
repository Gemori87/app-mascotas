#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Archivo de prueba para verificar la generación de PDFs de historias clínicas
"""

import mysql.connector
from config import Config
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from datetime import datetime

def generar_pdf_prueba():
    """Genera un PDF de prueba para verificar que la funcionalidad funciona"""
    try:
        # Conectar a la base de datos
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_DATABASE,
            port=Config.DB_PORT
        )
        cursor = conn.cursor(dictionary=True)
        
        # Obtener la primera historia clínica
        cursor.execute("""
            SELECT 
                hc.*,
                m.nombre as nombre_mascota,
                m.codigo as codigo_mascota,
                m.sexo,
                m.fecha_nac,
                TIMESTAMPDIFF(YEAR, m.fecha_nac, CURDATE()) as edad_años,
                TIMESTAMPDIFF(MONTH, m.fecha_nac, CURDATE()) % 12 as edad_meses,
                r.nombre as raza,
                CONCAT(p.nom1, ' ', p.apell1) as nombre_propietario,
                p.correo as correo_propietario,
                p.tele as telefono_propietario
            FROM historia_clinica hc
            JOIN mascota m ON hc.idmascota = m.Idmascota
            JOIN raza r ON m.idraza = r.Idraza
            JOIN persona p ON m.idduenio = p.Idpersona
            WHERE hc.estado = TRUE
            LIMIT 1
        """)
        historia = cursor.fetchone()
        
        if not historia:
            print("❌ No se encontraron historias clínicas")
            return
        
        print(f"✅ Historia clínica encontrada: {historia['nombre_mascota']}")
        
        # Generar PDF
        filename = f"historia_clinica_{historia['nombre_mascota']}_prueba.pdf"
        doc = SimpleDocTemplate(filename, pagesize=A4, 
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            textColor=colors.HexColor('#2563eb'),
            alignment=1  # Centrado
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor('#1f2937'),
            leftIndent=0
        )
        
        story = []
        
        # Título principal
        story.append(Paragraph("HISTORIA CLÍNICA VETERINARIA", title_style))
        story.append(Spacer(1, 20))
        
        # Información básica
        story.append(Paragraph("INFORMACIÓN BÁSICA", heading_style))
        
        basic_data = [
            ['Historia Clínica N°:', str(historia['Idhistoria'])],
            ['Fecha de Apertura:', historia['fecha_apertura'].strftime('%d/%m/%Y') if historia['fecha_apertura'] else 'N/A'],
            ['Mascota:', historia['nombre_mascota']],
            ['Código:', historia['codigo_mascota']],
            ['Raza:', historia['raza']],
            ['Sexo:', historia['sexo']],
            ['Edad:', f"{historia['edad_años']} años, {historia['edad_meses']} meses" if historia['edad_años'] else 'N/A'],
            ['Propietario:', historia['nombre_propietario']],
            ['Teléfono:', historia['telefono_propietario'] or 'N/A'],
            ['Email:', historia['correo_propietario'] or 'N/A']
        ]
        
        basic_table = Table(basic_data, colWidths=[2.5*inch, 3.5*inch])
        basic_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(basic_table)
        story.append(Spacer(1, 20))
        
        # Motivo de apertura
        if historia.get('motivo_apertura'):
            story.append(Paragraph("MOTIVO DE APERTURA", heading_style))
            story.append(Paragraph(historia['motivo_apertura'], styles['Normal']))
            story.append(Spacer(1, 12))
        
        # Pie de página
        story.append(Spacer(1, 40))
        footer_text = f"Documento generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')} - Archivo de prueba"
        story.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.gray, alignment=1)))
        
        # Construir PDF
        doc.build(story)
        
        print(f"✅ PDF generado exitosamente: {filename}")
        print(f"📄 Archivo guardado en: {filename}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error al generar PDF: {e}")

if __name__ == "__main__":
    print("🔄 Generando PDF de prueba...")
    generar_pdf_prueba()
