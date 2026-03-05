import time
import logging
from typing import List, Dict, Tuple, Optional, Set
from itertools import permutations, combinations
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException

class TriangularArbitrageBot:
    def __init__(self, api_key=None, api_secret=None, paper_mode=True, config=None):
        """
        Inicializa el bot de arbitraje triangular
        
        Args:
            api_key: API key de Binance (necesaria para trading real)
            api_secret: API secret de Binance (necesaria para trading real)
            paper_mode: Si True, solo simula operaciones
            config: Diccionario con configuración personalizada
        """
        self.paper_mode = paper_mode
        self.config = {
            'assets': ['BTC', 'ETH', 'DOGE'],  # Más activos aumentan oportunidades
            'stablecoins': ['USDT'],  # Múltiples stablecoins
            'min_profit': 0.0015,  # 0.15%
            'commission': 0.001,    # 0.1%
            'cooldown': 3,          # segundos entre operaciones
            'max_trade_amount': 100, # cantidad maxima a operar
            'min_notional': 10,     # mínimo $10 por orden en Binance
            'initial_balance': {
                'USDT': 5000,
                'USDC': 5000,
                'BTC': 0.05,
                'ETH': 0.5,
                'BNB': 5,
                'SOL': 10
            }
        }
        
        # Configurar logging
        logging.basicConfig(
            filename='arbitrage_bot.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filemode='a'
        )
        self.logger = logging.getLogger()
        
        # Inicializar API de Binance
        self.client = Client(
            api_key=api_key, 
            api_secret=api_secret,
            tld='com',
            testnet=self.paper_mode
        ) if api_key and api_secret else Client()
        
        # Estados del bot
        self.balance = self.config['initial_balance'].copy()
        self.triangles = []
        self.valid_pairs = set()
        self.pairs_to_watch = set()
        self.last_execution = 0
        self.trade_count = 0
        self.running = True

    def initialize(self):
        """Inicializa el bot y detecta triángulos disponibles"""
        self.logger.info("Inicializando bot de arbitraje triangular")
        
        try:
            # Verificar conexión con Binance
            self.client.get_exchange_info()
            self.logger.info("Conexion con Binance establecida correctamente")
            
            # Construir triángulos
            self._build_triangles()
            
            if not self.triangles:
                self.logger.warning("No se encontraron triángulos de arbitraje válidos")
            
            self.logger.info(f"Balance inicial: {self.balance}")
            self.logger.info(f"Modo: {'PAPER TRADING' if self.paper_mode else 'TRADING REAL'}")
            
        except Exception as e:
            self.logger.error(f"Error al inicializar: {str(e)}")
            raise
    
    def _build_triangles(self):
        """Construye triángulos de arbitraje válidos para Binance"""
        try:
            # 1. Obtener símbolos disponibles
            exchange_info = self.client.get_exchange_info()
            symbol_info = {symbol['symbol']: symbol['status'] 
                      for symbol in exchange_info['symbols']}
            # Mantener también el conjunto de símbolos para _suggest_missing_pairs
            all_symbols = {symbol['symbol'] for symbol in exchange_info['symbols']}
            
            
            assets = self.config['assets']
            stablecoins = self.config['stablecoins']
            self.triangles = []
            self.valid_pairs = set()
            self.pairs_to_watch = set()

            # 2. Identificar todos los pares válidos (asset/asset y asset/stable)
            for base, quote in permutations(assets, 2):
                pair = f"{base}{quote}"
                if pair in symbol_info and 'TRADING' in symbol_info[pair]:
                    pair_str = f"{base}/{quote}"
                    self.valid_pairs.add(pair_str)
        
            for asset in assets:
                for stable in stablecoins:
                    pair = f"{asset}{stable}"
                    if pair in symbol_info and 'TRADING' in symbol_info[pair]:
                        pair_str = f"{asset}/{stable}"
                        self.valid_pairs.add(pair_str)

            # 3. Buscar triángulos tipo A → B → C → A (sin stablecoins)
            for a, b, c in permutations(assets, 3):
                ab = f"{a}/{b}"
                bc = f"{b}/{c}"
                ca = f"{c}/{a}"
                
                if ab in self.valid_pairs and bc in self.valid_pairs and ca in self.valid_pairs:
                    triangle = [ab, bc, ca]
                    self.triangles.append(triangle)
                    self.pairs_to_watch.update(triangle)
                    self.logger.debug(f"Triangulo directo: {' , '.join(triangle)}")

            # 4. Buscar triángulos tipo A → USDT → B → A
            for a, b in combinations(assets, 2):
                for stable in stablecoins:
                    a_stable = f"{a}/{stable}"
                    b_stable = f"{b}/{stable}"
                    ab = f"{a}/{b}"
                    ba = f"{b}/{a}"
                    
                    # Patrón 1: A → USDT → B → A
                    if (a_stable in self.valid_pairs and 
                        b_stable in self.valid_pairs and 
                        ba in self.valid_pairs):
                        triangle = [a_stable, b_stable, ba]
                        self.triangles.append(triangle)
                        self.pairs_to_watch.update(triangle)
                        self.logger.debug(f"Triangulo con stable: {' , '.join(triangle)}")
                    
                    # Patrón 2: A → B → USDT → A (alternativo)
                    if (ab in self.valid_pairs and 
                        b_stable in self.valid_pairs and 
                        a_stable in self.valid_pairs):
                        triangle = [ab, b_stable, a_stable]
                        self.triangles.append(triangle)
                        self.pairs_to_watch.update(triangle)
                        self.logger.info(f"Triangulo alternativo: {' , '.join(triangle)}")

            # 5. Resultados finales
            if self.triangles:
                self.config['pairs_to_watch'] = list(self.pairs_to_watch)
                self.logger.info(f"Triángulos encontrados: {len(self.triangles)}")
                for i, triangle in enumerate(self.triangles, 1):
                    self.logger.info(f"{i}. {' , '.join(triangle)}")
            else:
                self.logger.warning("No se encontraron triángulos de arbitraje")
                self._suggest_missing_pairs(assets, all_symbols)
                self.config['pairs_to_watch'] = list(self.valid_pairs)  # Vigilar todos los pares válidos

        except Exception as e:
            self.logger.error(f"Error en _build_triangles: {str(e)}", exc_info=True)
            raise RuntimeError(f"Error al construir triángulos: {str(e)}")
   

    def _suggest_missing_pairs(self, assets: List[str], all_symbols: Set[str]):
        """Sugiere pares faltantes que podrían completar triángulos"""
        self.logger.info("Analizando pares faltantes que podrían completar triángulos...")
        missing_pairs = set()
        
        for a, b, c in combinations(assets, 3):
            for path in permutations([a, b, c]):
                required_pairs = [
                    f"{path[0]}/{path[1]}",
                    f"{path[1]}/{path[2]}",
                    f"{path[2]}/{path[0]}"
                ]
                
                missing = [pair for pair in required_pairs 
                          if pair.replace('/', '') not in all_symbols]
                
                if len(missing) == 1:
                    missing_pairs.add(missing[0])
        
        if missing_pairs:
            self.logger.info("Pares faltantes que podrían completar triángulos:")
            for pair in sorted(missing_pairs):
                self.logger.info(f"- {pair}")
        else:
            self.logger.info("No se identificaron pares faltantes obvios para completar triángulos")

    def get_current_prices(self) -> Dict[str, Dict]:
        """Obtiene los precios actuales de Binance con profundidad de mercado"""
        prices = {}
        
        if not self.config['pairs_to_watch']:
            self.logger.error("No hay pares configurados para vigilar")
            return prices
            
        for symbol in self.config['pairs_to_watch']:
            binance_symbol = symbol.replace('/', '')
            
            try:
                order_book = self.client.get_order_book(symbol=binance_symbol, limit=5)
                
                if not order_book or 'bids' not in order_book or not order_book['bids']:
                    continue
                
                prices[symbol] = {
                    'bid': float(order_book['bids'][0][0]),
                    'ask': float(order_book['asks'][0][0]),
                    'bid_qty': float(order_book['bids'][0][1]),
                    'ask_qty': float(order_book['asks'][0][1]),
                    'symbol': binance_symbol
                }
                
            except Exception as e:
                self.logger.debug(f"Error obteniendo precio para {symbol}: {str(e)}")
                continue
                
        return prices

    def check_arbitrage(self, triangle: List[str], prices: Dict) -> Optional[Tuple[float, List[str]]]:
        """Verifica si existe oportunidad de arbitraje en el triángulo"""
        max_profit = 0
        best_path = None
        
        for path in self._generate_valid_paths(triangle):
            try:
                p1_data = prices[path[0]]
                p2_data = prices[path[1]]
                p3_data = prices[path[2]]
                
                p1_ask = p1_data['ask']
                p2_ask = p2_data['ask']
                p3_bid = p3_data['bid']
                
                slippage = 0.01
                effective_p1 = p1_ask * (1 + slippage)
                effective_p2 = p2_ask * (1 + slippage)
                effective_p3 = p3_bid * (1 - slippage)
                
                effective_rate = (1 / effective_p1) * (1 / effective_p2) * effective_p3 
                effective_rate *= (1 - self.config['commission'])**3
                profit = (effective_rate - 1) * 100
                
                min_liquidity = min(
                    p1_data['ask_qty'] * p1_ask,
                    p2_data['ask_qty'] * p2_ask,
                    p3_data['bid_qty'] * p3_bid
                )
                
                if profit > max_profit and profit > self.config['min_profit'] and min_liquidity > self.config['min_notional']:
                    max_profit = profit
                    best_path = path
                    
            except KeyError:
                continue
                
        return (max_profit, best_path) if best_path else None

    def _generate_valid_paths(self, triangle: List[str]) -> List[List[str]]:
        """Genera todas las rutas válidas para el triángulo"""
        valid_paths = []
        a, b, c = triangle[0].split('/')[0], triangle[1].split('/')[0], triangle[2].split('/')[0]
        
        standard_paths = [
            [f"{a}/{b}", f"{b}/{c}", f"{c}/{a}"],
            [f"{a}/{c}", f"{c}/{b}", f"{b}/{a}"]
        ]
        
        if f"{b}/{a}" in self.valid_pairs:
            standard_paths.append([f"{b}/{a}", f"{a}/{c}", f"{c}/{b}"])
        
        if f"{c}/{a}" in self.valid_pairs:
            standard_paths.append([f"{c}/{a}", f"{a}/{b}", f"{b}/{c}"])
        
        for path in standard_paths:
            if all(p in self.valid_pairs for p in path):
                valid_paths.append(path)
        
        return valid_paths

    def execute_trade(self, path: List[str], amount: float, prices: Dict):
        """Ejecuta el arbitraje y provee feedback detallado"""
        self.trade_count += 1
        trade_id = f"TRADE-{self.trade_count:04d}"
        
        # Feedback inicial
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"{trade_id} - INICIANDO OPERACIÓN")
        self.logger.info(f"Camino: {' → '.join(path)}")
        self.logger.info(f"Monto inicial: {amount:.6f} {path[0].split('/')[1]}")
        self.logger.info(f"Precios actuales: {prices}")
        for pair in path:
            self.logger.info(f"  {pair}: Bid={prices[pair]['bid']:.8f} | Ask={prices[pair]['ask']:.8f}")
        
        try:
            start_time = time.time()
            
            if self.paper_mode:
                result = self._execute_paper_trade(trade_id, path, amount, prices)
            else:
                result = self._execute_real_trade(trade_id, path, amount, prices)
            
            # Feedback final
            execution_time = time.time() - start_time
            if result:
                self.logger.info(f"{trade_id} - OPERACIÓN EXITOSA")
            else:
                self.logger.warning(f"{trade_id} - OPERACIÓN FALLIDA")
            
            self.logger.info(f"Tiempo ejecución: {execution_time:.2f} segundos")
            self.logger.info(f"{'='*60}\n")
            return result
            
        except Exception as e:
            self.logger.error(f"{trade_id} - ERROR DURANTE EJECUCIÓN: {str(e)}")
            self.logger.info(f"{'='*60}\n")
            return False

    def _execute_paper_trade(self, trade_id: str, path: List[str], amount: float, prices: Dict):
        """Ejecuta simulación de trade con feedback detallado"""
        initial_balance = self.balance.copy()
        
        try:
            # Feedback inicial
            self.logger.info(f"\n{trade_id} - FASE 1: COMPRA INICIAL")
            pair1 = path[0]
            base1, quote1 = pair1.split('/')
            p1_data = prices[pair1]
            price1 = p1_data['ask']
            cost1 = amount * price1
            
            self.logger.info(f"Comprando {amount:.6f} {base1} con {cost1:.6f} {quote1}")
            self.logger.info(f"Precio de compra: {price1:.8f} {quote1}")
            self.logger.info(f"Liquidez disponible: {p1_data['ask_qty']:.4f} @ {price1:.8f}")
            
            if self.balance.get(quote1, 0) < cost1:
                self.logger.warning(f"{trade_id} - Fondos insuficientes en {quote1}")
                return False
                
            amount_after_fee1 = amount * (1 - self.config['commission'])
            self.balance[quote1] -= cost1
            self.balance[base1] = self.balance.get(base1, 0) + amount_after_fee1
            
            # Feedback intermedio
            self.logger.info(f"\n{trade_id} - RESULTADO PARCIAL:")
            self.logger.info(f"Balance actual: {self.balance}")
            
            # Paso 2: Feedback de conversión
            self.logger.info(f"\n{trade_id} - FASE 2: CONVERSIÓN")
            pair2 = path[1]
            base2, quote2 = pair2.split('/')
            p2_data = prices[pair2]
            amount2 = self.balance[base1]
            price2 = p2_data['ask']
            cost2 = amount2 * price2
            
            self.logger.info(f"Comprando {amount2:.6f} {base2} con {amount2:.6f} {base1}")
            self.logger.info(f"Precio de compra: {price2:.8f} {quote2}")
            self.logger.info(f"Liquidez disponible: {p2_data['ask_qty']:.4f} @ {price2:.8f}")
            
            amount_after_fee2 = amount2 * (1 - self.config['commission']) / price2
            self.balance[base1] -= amount2
            self.balance[base2] = self.balance.get(base2, 0) + amount_after_fee2
            
            # Paso 3: Feedback final
            self.logger.info(f"\n{trade_id} - FASE 3: VENTA FINAL")
            pair3 = path[2]
            base3, quote3 = pair3.split('/')
            p3_data = prices[pair3]
            amount3 = self.balance[base2]
            price3 = p3_data['bid']
            revenue_before_fee = amount3 * price3
            
            self.logger.info(f"Vendiendo {amount3:.6f} {base2} por {revenue_before_fee:.6f} {quote3}")
            self.logger.info(f"Precio de venta: {price3:.8f} {quote3}")
            self.logger.info(f"Liquidez disponible: {p3_data['bid_qty']:.4f} @ {price3:.8f}")
            
            revenue_after_fee = revenue_before_fee * (1 - self.config['commission'])
            self.balance[base2] -= amount3
            self.balance[quote3] = self.balance.get(quote3, 0) + revenue_after_fee
            
            # Cálculo y feedback de resultados
            initial_investment = amount * price1
            final_amount = revenue_after_fee
            profit = final_amount - initial_investment
            profit_pct = (profit / initial_investment) * 100
            
            self.logger.info(f"\n{trade_id} - RESUMEN FINAL")
            self.logger.info(f"Profit: {profit:.6f} {quote3} ({profit_pct:.2f}%)")
            self.logger.info(f"Balance inicial: {initial_balance}")
            self.logger.info(f"Balance final: {self.balance}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"{trade_id} - ERROR EN SIMULACIÓN: {str(e)}")
            self.balance = initial_balance  # Revertir balance
            return False

    def _execute_real_trade(self, trade_id: str, path: List[str], amount: float, prices: Dict):
        """Ejecuta el arbitraje real en Binance con feedback detallado"""
        initial_balance = self._get_current_balance()
        self.logger.info(f"\n{trade_id} - BALANCE INICIAL REAL: {initial_balance}")
        
        try:
            start_time = time.time()
            
            # Paso 1: Primera orden
            pair1 = path[0]
            base1, quote1 = pair1.split('/')
            binance_symbol1 = prices[pair1]['symbol']
            price1 = prices[pair1]['ask']
            cost1 = amount * price1
            
            self.logger.info(f"\n{trade_id} - FASE 1: COMPRA INICIAL")
            self.logger.info(f"Par: {pair1} | Símbolo Binance: {binance_symbol1}")
            self.logger.info(f"Intentando comprar {amount:.6f} {base1} con {cost1:.6f} {quote1}")
            self.logger.info(f"Precio de compra: {price1:.8f} {quote1}")
            self.logger.info(f"Liquidez disponible: {prices[pair1]['ask_qty']:.4f} @ {price1:.8f}")
            
            if initial_balance.get(quote1, 0) < cost1:
                self.logger.warning(f"{trade_id} - Fondos insuficientes en {quote1}")
                return False
                
            if cost1 < self.config['min_notional']:
                self.logger.warning(f"{trade_id} - Orden muy pequeña (${cost1:.2f} < ${self.config['min_notional']})")
                return False
                
            try:
                order1 = self.client.create_order(
                    symbol=binance_symbol1,
                    side=SIDE_BUY,
                    type=ORDER_TYPE_MARKET,
                    quoteOrderQty=round(cost1, 6))
                
                self.logger.info(f"{trade_id} - ORDEN 1 EJECUTADA:")
                self.logger.info(f"ID: {order1['orderId']} | Estado: {order1['status']}")
                self.logger.info(f"Ejecutado: {order1['executedQty']} {base1} a {order1['fills'][0]['price']} {quote1}")
            except BinanceAPIException as e:
                self.logger.error(f"{trade_id} - ERROR EN ORDEN 1: {e.status_code} {e.message}")
                return False
                
            time.sleep(0.5)
            
            # Paso 2: Segunda orden
            pair2 = path[1]
            base2, quote2 = pair2.split('/')
            binance_symbol2 = prices[pair2]['symbol']
            
            current_balance = self._get_current_balance()
            amount2 = current_balance.get(base1, 0)
            
            self.logger.info(f"\n{trade_id} - FASE 2: CONVERSIÓN")
            self.logger.info(f"Par: {pair2} | Símbolo Binance: {binance_symbol2}")
            self.logger.info(f"Intentando comprar con {amount2:.6f} {base1}")
            self.logger.info(f"Precio de compra: {prices[pair2]['ask']:.8f} {quote2}")
            self.logger.info(f"Liquidez disponible: {prices[pair2]['ask_qty']:.4f} @ {prices[pair2]['ask']:.8f}")
            
            if amount2 <= 0:
                self.logger.warning(f"{trade_id} - Balance de {base1} insuficiente para paso 2")
                return False
                
            try:
                order2 = self.client.create_order(
                    symbol=binance_symbol2,
                    side=SIDE_BUY,
                    type=ORDER_TYPE_MARKET,
                    quantity=round(amount2, 6))
                
                self.logger.info(f"{trade_id} - ORDEN 2 EJECUTADA:")
                self.logger.info(f"ID: {order2['orderId']} | Estado: {order2['status']}")
                self.logger.info(f"Ejecutado: {order2['executedQty']} {base2}")
            except BinanceAPIException as e:
                self.logger.error(f"{trade_id} - ERROR EN ORDEN 2: {e.status_code} {e.message}")
                return False
                
            time.sleep(0.5)
            
            # Paso 3: Tercera orden
            pair3 = path[2]
            base3, quote3 = pair3.split('/')
            binance_symbol3 = prices[pair3]['symbol']
            
            current_balance = self._get_current_balance()
            amount3 = current_balance.get(base2, 0)
            
            self.logger.info(f"\n{trade_id} - FASE 3: VENTA FINAL")
            self.logger.info(f"Par: {pair3} | Símbolo Binance: {binance_symbol3}")
            self.logger.info(f"Intentando vender {amount3:.6f} {base2}")
            self.logger.info(f"Precio de venta: {prices[pair3]['bid']:.8f} {quote3}")
            self.logger.info(f"Liquidez disponible: {prices[pair3]['bid_qty']:.4f} @ {prices[pair3]['bid']:.8f}")
            
            if amount3 <= 0:
                self.logger.warning(f"{trade_id} - Balance de {base2} insuficiente para paso 3")
                return False
                
            try:
                order3 = self.client.create_order(
                    symbol=binance_symbol3,
                    side=SIDE_SELL,
                    type=ORDER_TYPE_MARKET,
                    quantity=round(amount3, 6))
                
                self.logger.info(f"{trade_id} - ORDEN 3 EJECUTADA:")
                self.logger.info(f"ID: {order3['orderId']} | Estado: {order3['status']}")
                self.logger.info(f"Ejecutado: {order3['executedQty']} {base2}")
            except BinanceAPIException as e:
                self.logger.error(f"{trade_id} - ERROR EN ORDEN 3: {e.status_code} {e.message}")
                return False
                
            final_balance = self._get_current_balance()
            
            initial_amount = initial_balance.get(quote1, 0)
            final_amount = final_balance.get(quote3, 0)
            profit = final_amount - initial_amount
            profit_pct = (profit / initial_amount) * 100 if initial_amount > 0 else 0
            
            execution_time = time.time() - start_time
            
            self.logger.info(f"\n{trade_id} - RESUMEN FINAL")
            self.logger.info(f"Profit estimado: {profit:.6f} {quote3} ({profit_pct:.4f}%)")
            self.logger.info(f"Balance inicial: {initial_balance}")
            self.logger.info(f"Balance final: {final_balance}")
            self.logger.info(f"Tiempo ejecución: {execution_time:.2f} segundos")
            
            return True
            
        except Exception as e:
            self.logger.error(f"{trade_id} - ERROR EN TRADING REAL: {str(e)}")
            return False

    def _get_current_balance(self) -> Dict[str, float]:
        """Obtiene el balance actual de la cuenta en Binance"""
        if self.paper_mode:
            return self.balance.copy()
            
        try:
            account = self.client.get_account()
            balance = {}
            
            for asset in account['balances']:
                free = float(asset['free'])
                if free > 0.00000001:
                    balance[asset['asset']] = free
            
            return balance
        except Exception as e:
            self.logger.error(f"Error al obtener balance real: {str(e)}")
            return {}

    def stop(self):
        """Detiene el bot de manera controlada"""
        self.running = False
        self.logger.info("Bot detenido por el usuario")

    def run(self):
        """Loop principal del bot"""
        self.initialize()
        
        while self.running:
            try:
                current_time = time.time()
                if current_time - self.last_execution < self.config['cooldown']:
                    time.sleep(1)
                    continue
                
                print("\n" + "="*50)
                print(f"Ciclo de análisis - {time.strftime('%H:%M:%S')}")
                print("="*50)
                
                prices = self.get_current_prices()
                if not prices:
                    print("No se obtuvieron precios. Reintentando...")
                    time.sleep(5)
                    continue
                
                print("Buscando oportunidades...")
                opportunity_found = False

                for triangle in self.triangles:
                    result = self.check_arbitrage(triangle, prices)
                    if result:
                        profit, path = result
                        quote_currency = path[0].split('/')[1]
                        available = self.balance.get(quote_currency, 0)
                        amount = min(available, self.config['max_trade_amount'])
                    
                        if amount > 0.001:
                            print(f"Oportunidad detectada! Profit: {profit:.2f}%")
                            self.logger.info(f"Oportunidad detectada! Profit: {profit:.2f}%")
                            print(f"   Camino: {' , '.join(path)}")
                            if self.execute_trade(path, amount, prices):
                                self.last_execution = time.time()
                                opportunity_found = True
                                break
                
                if not opportunity_found:
                    print("No hay oportunidades. Próximo análisis en 1s...")
                    time.sleep(1)
                
            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                print(f"Error: {str(e)}")
                time.sleep(5)

if __name__ == '__main__':
     
    # Para trading real, proporciona tu API key y secret
    api_key = None  # Reemplaza con tu API key
    api_secret = None  # Reemplaza con tu API secret
    
    # Inicializar bot
    bot = TriangularArbitrageBot(
        api_key=api_key,
        api_secret=api_secret,
        paper_mode=True,  # Cambiar a False para trading real
    )
    
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()