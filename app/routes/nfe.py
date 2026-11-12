import logging
from flask import Blueprint, request, jsonify, Response
from datetime import datetime
import tempfile
import os

logger = logging.getLogger(__name__)

nfe_bp = Blueprint('nfe', __name__, url_prefix='/nfe')


# ENDPOINTS DE PDF - CORRIGIDOS

@nfe_bp.route('/pdf/view/<int:order_id>', methods=['GET'])
def view_danfe_pdf(order_id):
    """
    ✅ VISUALIZAR PDF do DANFE no navegador (inline) - VERSÃO CORRIGIDA
    
    Abre o PDF diretamente no navegador sem forçar download.
    URL: /nfe/pdf/view/{order_id}
    """
    try:
        logger.info(f"[PDF VIEW] Pedido #{order_id}")
        
        # LAZY IMPORT: Evita circular imports
        from services.woocommerce.client import WooCommerceClient
        from services.sankhya.service import SankhyaServiceContext
        
        # 1. Buscar NUNOTA do WooCommerce metadata
        woo_client = WooCommerceClient()
        order = woo_client.get_order(order_id)
        
        if not order:
            logger.warning(f"Pedido #{order_id} não encontrado")
            return jsonify({'error': 'Pedido não encontrado'}), 404
        
        # 2. Extrair NUNOTA dos metadados
        nunota = None
        for meta in order.get('meta_data', []):
            if meta.get('key') == '_sankhya_nunota':
                nunota = int(meta.get('value', 0))
                break
        
        if not nunota:
            logger.warning(f"NUNOTA não encontrada para pedido #{order_id}")
            return jsonify({'error': 'NFe ainda não disponível'}), 404
        
        logger.info(f"NUNOTA {nunota} encontrada")
        
        # 3. Buscar XML da NFe no Sankhya
        with SankhyaServiceContext() as service:
            xml_content = service._obter_xml_nfe_por_nunota(nunota, order_id=order_id)
            
            if not xml_content:
                logger.error(f"XML não encontrado para NUNOTA {nunota}")
                return jsonify({'error': 'XML da NFe não disponível'}), 404
        
        # 4. Gerar PDF usando BrazilFiscalReport - MÉTODO CORRETO
        from brazilfiscalreport.danfe import Danfe
        
        # FIX: Usar arquivo temporário para garantir bytes corretos
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            temp_pdf_path = tmp.name
        
        try:
            # Gerar PDF em arquivo temporário
            danfe = Danfe(xml=xml_content)
            danfe.output(temp_pdf_path)  # Salva em arquivo
            
            # Verificar se arquivo foi criado
            if not os.path.exists(temp_pdf_path):
                raise RuntimeError("Arquivo PDF não foi criado")
            
            file_size = os.path.getsize(temp_pdf_path)
            if file_size == 0:
                raise ValueError("PDF gerado está vazio")
            
            # Ler arquivo como BYTES
            with open(temp_pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
            logger.info(f"PDF gerado com sucesso para pedido #{order_id} ({file_size} bytes)")
            
        finally:
            # Sempre limpar arquivo temporário
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
        
        # 5. Retornar PDF para VISUALIZAÇÃO (inline) - AGORA COM BYTES CORRETOS
        return Response(
            pdf_bytes,  # Agora é bytes de verdade!
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'inline; filename="DANFE_Pedido_{order_id}.pdf"',
                'Content-Type': 'application/pdf',
                'Content-Length': str(len(pdf_bytes))
            }
        )
        
    except ImportError as e:
        logger.error(f"Erro de importação: {e}")
        return jsonify({'error': 'Biblioteca BrazilFiscalReport não encontrada'}), 500
        
    except Exception as e:
        logger.error(f"Erro ao visualizar PDF: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@nfe_bp.route('/pdf/download/<int:order_id>', methods=['GET'])
def download_danfe_pdf(order_id):
    """
    ✅ DOWNLOAD do PDF do DANFE (força download) - VERSÃO CORRIGIDA
    
    Força o download do PDF ao invés de abrir no navegador.
    URL: /nfe/pdf/download/{order_id}
    """
    try:
        logger.info(f"[PDF DOWNLOAD] Pedido #{order_id}")
        
        # LAZY IMPORT
        from services.woocommerce.client import WooCommerceClient
        from services.sankhya.service import SankhyaServiceContext
        
        # 1. Buscar NUNOTA do WooCommerce
        woo_client = WooCommerceClient()
        order = woo_client.get_order(order_id)
        
        if not order:
            logger.warning(f"Pedido #{order_id} não encontrado")
            return jsonify({'error': 'Pedido não encontrado'}), 404
        
        # 2. Extrair NUNOTA dos metadados
        nunota = None
        for meta in order.get('meta_data', []):
            if meta.get('key') == '_sankhya_nunota':
                nunota = int(meta.get('value', 0))
                break
        
        if not nunota:
            logger.warning(f"NUNOTA não encontrada para pedido #{order_id}")
            return jsonify({'error': 'NFe ainda não disponível'}), 404
        
        logger.info(f"NUNOTA {nunota} encontrada")
        
        # 3. Buscar XML da NFe
        with SankhyaServiceContext() as service:
            xml_content = service._obter_xml_nfe_por_nunota(nunota, order_id=order_id)
            
            if not xml_content:
                logger.error(f"XML não encontrado para NUNOTA {nunota}")
                return jsonify({'error': 'XML da NFe não disponível'}), 404
        
        # 4. Gerar PDF - MÉTODO CORRETO
        from brazilfiscalreport.danfe import Danfe
        
        # FIX: Usar arquivo temporário
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            temp_pdf_path = tmp.name
        
        try:
            danfe = Danfe(xml=xml_content)
            danfe.output(temp_pdf_path)  # Salva em arquivo
            
            if not os.path.exists(temp_pdf_path):
                raise RuntimeError("Arquivo PDF não foi criado")
            
            file_size = os.path.getsize(temp_pdf_path)
            if file_size == 0:
                raise ValueError("PDF gerado está vazio")
            
            # Ler arquivo como BYTES
            with open(temp_pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
            logger.info(f"PDF gerado para download do pedido #{order_id} ({file_size} bytes)")
            
        finally:
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
        
        # 5. Retornar PDF para DOWNLOAD (attachment) - COM BYTES CORRETOS
        return Response(
            pdf_bytes,  # Agora é bytes de verdade!
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="DANFE_Pedido_{order_id}.pdf"',
                'Content-Type': 'application/pdf',
                'Content-Length': str(len(pdf_bytes))
            }
        )
        
    except ImportError as e:
        logger.error(f"Erro de importação: {e}")
        return jsonify({'error': 'Biblioteca BrazilFiscalReport não encontrada'}), 500
        
    except Exception as e:
        logger.error(f"Erro ao fazer download: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ENDPOINT DE VERIFICAÇÃO (útil para debug)

@nfe_bp.route('/check/<int:order_id>', methods=['GET'])
def check_nfe_status(order_id):
    """
    ✅ Verifica se NFe está disponível
    
    Retorna JSON com status da NFe.
    URL: /nfe/check/{order_id}
    """
    try:
        logger.info(f"[NFe CHECK] Pedido #{order_id}")
        
        from services.woocommerce.client import WooCommerceClient
        
        # Buscar pedido
        woo_client = WooCommerceClient()
        order = woo_client.get_order(order_id)
        
        if not order:
            return jsonify({
                'order_id': order_id,
                'status': 'order_not_found',
                'available': False,
                'message': 'Pedido não encontrado'
            }), 404
        
        # Verificar NUNOTA
        nunota = None
        for meta in order.get('meta_data', []):
            if meta.get('key') == '_sankhya_nunota':
                nunota = int(meta.get('value', 0))
                break
        
        if not nunota:
            return jsonify({
                'order_id': order_id,
                'status': 'nfe_not_generated',
                'available': False,
                'message': 'NFe ainda não foi gerada para este pedido'
            }), 200
        
        # NFe disponível
        return jsonify({
            'order_id': order_id,
            'nunota': nunota,
            'status': 'available',
            'available': True,
            'message': 'NFe disponível para visualização',
            'urls': {
                'view': f'/nfe/pdf/view/{order_id}',
                'download': f'/nfe/pdf/download/{order_id}'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao verificar NFe: {e}", exc_info=True)
        return jsonify({
            'order_id': order_id,
            'status': 'error',
            'available': False,
            'error': str(e)
        }), 500


# ENDPOINT DE SAÚDE

@nfe_bp.route('/health', methods=['GET'])
def health():
    """Health check do módulo NFe"""
    return jsonify({
        'status': 'healthy',
        'module': 'nfe',
        'endpoints': {
            'view': '/nfe/pdf/view/<order_id>',
            'download': '/nfe/pdf/download/<order_id>',
            'check': '/nfe/check/<order_id>'
        }
    }), 200
