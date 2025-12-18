import json
import math
import networkx as nx
import os

class NetworkCostCalculator:
    def __init__(self, json_file_path, w_delay=0.33, w_rel=0.33, w_res=0.34):
        self.w_delay = w_delay
        self.w_rel = w_rel
        self.w_res = w_res
        self.G = self.load_network(json_file_path)

    def load_network(self, file_path):
        """test_network.json dosyasını sizin formatınıza özel olarak yükler."""
        try:
            if not os.path.exists(file_path):
                print(f"❌ Dosya bulunamadı: {file_path}")
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            G = nx.Graph()
            
            # --- 1. DÜĞÜMLERİ YÜKLEME (Sözlük Yapısı İçin Düzeltildi) ---
            # Sizin dosyanızda nodes: {'0': {...}, '1': {...}} şeklinde
            if 'nodes' in data:
                nodes_data = data['nodes']
                
                # Eğer sözlükse (dict) .items() ile dön
                if isinstance(nodes_data, dict):
                    for node_id, attrs in nodes_data.items():
                        # node_id string gelebilir ('0'), int'e çevirmek gerekebilir
                        try:
                            n_id = int(node_id)
                        except:
                            n_id = node_id
                        
                        # JSON'daki 'reliability' -> Kodun beklediği 'node_reliability'
                        if 'reliability' in attrs:
                            attrs['node_reliability'] = attrs['reliability']
                            
                        G.add_node(n_id, **attrs)
                        
                # Eğer listeyse (eski format ihtimaline karşı)
                elif isinstance(nodes_data, list):
                    for node in nodes_data:
                        n_id = node.get('id')
                        G.add_node(n_id, **node)

            # --- 2. BAĞLANTILARI (EDGES) YÜKLEME ---
            # Sizin dosyanızda 'links' yerine 'edges' kullanılmış olabilir
            edges_list = data.get('edges', data.get('links', []))
            
            for edge in edges_list:
                u = edge.get('source')
                v = edge.get('target')
                
                # Kaynak ve Hedef ID'lerini de int'e çevirelim (uyum için)
                try:
                    u, v = int(u), int(v)
                except:
                    pass
                
                # JSON -> Kod Değişken Eşleştirmesi
                # Kod 'link_delay' ve 'link_reliability' bekliyor, JSON'da 'delay' ve 'reliability' var
                attrs = edge.copy()
                if 'delay' in attrs:
                    attrs['link_delay'] = attrs['delay']
                if 'reliability' in attrs:
                    attrs['link_reliability'] = attrs['reliability']
                
                G.add_edge(u, v, **attrs)
            
            print(f"✅ Ağ başarıyla yüklendi: {len(G.nodes)} düğüm, {len(G.edges)} bağlantı.")
            return G

        except Exception as e:
            print(f"❌ Kritik Yükleme Hatası: {e}")
            import traceback
            traceback.print_exc()
            return None

    def calculate_metrics(self, path):
        if not self.G:
            return {"valid": False, "message": "Grafik yüklenemedi."}
            
        if not path or len(path) < 2:
            return {"valid": False, "message": "Yol çok kısa veya boş."}

        total_delay = 0
        total_resource_cost = 0
        reliability_log_cost = 0 
        reliability_real = 1.0

        try:
            # --- NODE HESAPLAMALARI ---
            for node_id in path[1:-1]: # Ara düğümler
                if not self.G.has_node(node_id):
                     return {"valid": False, "message": f"Düğüm {node_id} yok."}
                
                node = self.G.nodes[node_id]
                
                # İşlem Gecikmesi
                p_delay = node.get('processing_delay', 0)
                total_delay += p_delay
                
                # Güvenilirlik
                # 'node_reliability' yoksa 'reliability'ye bak, o da yoksa 0.999
                rel = node.get('node_reliability', node.get('reliability', 0.999))
                
                reliability_real *= rel
                reliability_log_cost += -math.log(rel) if rel > 0 else 100

            # --- LINK HESAPLAMALARI ---
            for i in range(len(path) - 1):
                u, v = path[i], path[i+1]
                
                if not self.G.has_edge(u, v):
                    return {"valid": False, "message": f"Hat yok: {u}->{v}"}
                
                edge = self.G[u][v]
                
                # Gecikme
                l_delay = edge.get('link_delay', edge.get('delay', 0))
                total_delay += l_delay
                
                # Güvenilirlik
                l_rel = edge.get('link_reliability', edge.get('reliability', 0.999))
                
                reliability_real *= l_rel
                reliability_log_cost += -math.log(l_rel) if l_rel > 0 else 100
                
                # Kaynak
                bw = edge.get('bandwidth', 100)
                bw = bw if bw > 0 else 1 
                total_resource_cost += (1000.0 / bw)

            weighted_cost = (self.w_delay * total_delay) + \
                            (self.w_rel * reliability_log_cost) + \
                            (self.w_res * total_resource_cost)

            return {
                "valid": True,
                "path": path,
                "total_cost (Fitness)": round(weighted_cost, 4),
                "details": {
                    "Total Delay": round(total_delay, 4),
                    "Reliability (%)": round(reliability_real * 100, 4),
                    "Reliability Cost": round(reliability_log_cost, 4),
                    "Resource Cost": round(total_resource_cost, 4)
                }
            }
        except Exception as e:
            return {"valid": False, "message": f"Hesaplama hatası: {e}"}


# --- TEST KISMI ---
if __name__ == "__main__":
    import os
    
    script_konumu = os.path.dirname(os.path.abspath("app.py"))
    json_dosya_yolu = os.path.join(script_konumu, "test_network.json")
    
    print(f"📂 Dosya şurada aranıyor: {json_dosya_yolu}")

    # 3. Hesaplayıcıyı başlat
    calculator = NetworkCostCalculator(json_dosya_yolu)
    
    # 4. Yükleme başarılıysa test yap
    if calculator.G:
        try:
            # Test için kaynak (0) ve hedef (249) belirle
            source = 0
            target = 249
            
            # Eğer bu düğümler grafikte varsa testi çalıştır
            if calculator.G.has_node(source) and calculator.G.has_node(target):
                print(f"--- Test Başlıyor: {source} -> {target} ---")
                
                # NetworkX ile en kısa yolu bul (sadece test amaçlı)
                test_path = nx.shortest_path(calculator.G, source=source, target=target)
                print(f"Bulunan Yol: {test_path}")
                
                # Maliyetleri Hesapla
                result = calculator.calculate_metrics(test_path)
                
                # Sonucu ekrana güzelce yazdır
                print(json.dumps(result, indent=4, ensure_ascii=False))
            else:
                print(f"Hata: {source} veya {target} numaralı düğümler bu ağda yok.")
                
        except nx.NetworkXNoPath:
            print("❌ Hata: Bu iki düğüm arasında gidilecek bir yol yok (Ağ kopuk olabilir).")
        except Exception as e:
            print(f"❌ Beklenmedik Hata: {e}")
    else:
        print("❌ JSON dosyası yüklenemediği için test yapılamadı.")