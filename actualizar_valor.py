import datetime
import click
import requests
from pprint import pprint as pp

BASE_URL = 'https://api.argentinadatos.com/v1'


@click.group()
def cli():
    pass

def is_leap_year(year: int):

    if year % 100 == 0:
        return year % 400 == 0
    return year % 4 == 0 


def ultimo_dia_mes(year: int, month: int) -> int:

    ultimo_dia = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    dia = ultimo_dia[month - 1]

    if month == 2: 
        if is_leap_year(year):
            return 29

    return dia 

def get_dolar_before(fecha_inicio: datetime):
    ''' retorna el valor dolar blue  para la fecha ingresada '''

    fecha_inicio = fecha_inicio.strftime('%Y-%m-%d')
    year = fecha_inicio.split('-')[0]
    month = fecha_inicio.split('-')[1]
    day = fecha_inicio.split('-')[2]
    response  = requests.get(f'{BASE_URL}/cotizaciones/dolares/blue/{year}/{month}/{day}')

    if response.status_code == 200:
        return response.json()['compra']
    raise ValueError()

@cli.command('dolar-blue')
def get_dolar_today():
    ''' Imprime el ultimo valor dolar blue registrado '''

    response  = requests.get(f'{BASE_URL}/cotizaciones/dolares/blue')
    if response.status_code == 200:
        print(f'Dolar BLUE - Hoy >> $' + str(response.json()[-1]['compra']), '(Ayer - $' + str(response.json()[-2]['compra']) + ')')
        return
    raise ValueError()

def get_dolar():
    ''' retorna el ultimo valor dolar blue registrado '''

    response  = requests.get(f'{BASE_URL}/cotizaciones/dolares/blue')
    if response.status_code == 200:
        return response.json()[-1]['compra']
    raise ValueError()

def delta_usd(fecha_inicio: datetime, logs=False):
    
    dolar_historico = get_dolar_before(fecha_inicio)
    dolar_hoy  = get_dolar()
    if logs:
        print('\t [LOG] - Dolar HISTORICO: ', dolar_historico)
        print('\t [LOG] - Dolar HOY: ', dolar_hoy)
    return round((dolar_hoy - dolar_historico) / dolar_historico, 2) 

def delta_ipc(fecha_inicio: datetime = None, logs=False) -> float:
    ''' Calcula el valor acumulado de inflacion sumando el IPC mensual 
        desde la fecha de inicio hasta el ultimo dia del mes pasado '''

    response = requests.get(f"{BASE_URL}/finanzas/indices/inflacion") 

    data = response.json() 

    if not fecha_inicio:

        ultimo_valor_ipc = float(data[-1]['valor']) / 100
        return round(ultimo_valor_ipc, 2)

    # la API retorna un str en este formato     "fecha": "1995-04-30",
    fecha_inicio = fecha_inicio.strftime('%Y-%m-%d') 
    if logs:
        print('\t [LOG] - FECHA INICIO >>', fecha_inicio)

    if response.status_code != 200:
        raise Exception('[ERROR] - API connection error - STATUS CODE -' + str(response.status_code))
        return False
    
    for index in range(len(data)):
        # print('[LOG] - recorriendo en i =', index)
        if data[index]['fecha'] == fecha_inicio:
            if logs:
                print('\t [LOG] - ENCONTRE MI TARGET DATE')
            data = data[index:]
            if logs:
                print('\t [DATA]')
                pp(data)
                print('\t [LOG] - CANTIDAD INDICES MENSUALES (IPC) >>', len(data))
            break

    ipc_acumulado = 1 
    for d in data:

        indice = float(d['valor']) / 100
        ipc_acumulado = ipc_acumulado * (1 + indice) 

    ipc_acumulado = ipc_acumulado - 1 
    return round(ipc_acumulado, 2)

def formula_actualizacion(valor: float,
                      delta_ipc: float = 0,
                      delta_usd: float = 0,
                      ponderacion_ipc: float = 0.5,
                      ponderacion_usd: float = 0.5):

    if ponderacion_ipc + ponderacion_usd != 1:
        raise ValueError('[ERROR] - ponederacion IPC + ponderacion USD tiene que ser UNO')
    
    valor_actualizado = valor * (1 + ponderacion_ipc * delta_ipc + ponderacion_usd * delta_usd)
    return round(valor_actualizado, 2)
 
@cli.command('ipc')
def ultimo_ipc():

    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
             'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

    response = requests.get(f"{BASE_URL}/finanzas/indices/inflacion") 
    valor = response.json()[-1] 
    mes = int(valor['fecha'].split('-')[1])
    print(f'IPC {meses[mes]} >>', str(valor['valor']) + '%')

@cli.command('run-tests') 
def test():
    data = [
        {'nombre': 'expensas LM CAMPOS', 'anterior': 243205, 'actual': 250508},
        {'nombre': 'celular', 'anterior': 14199, 'actual': 14750},
        {'nombre': 'seguro-auto', 'anterior': 99734, 'actual': 102255},
        {'nombre': 'seguro-auto2', 'anterior': 106090, 'actual': 111394},
        {'nombre': 'osde', 'anterior': 355289, 'actual': 364548},
        {'nombre': 'fibertel-internet', 'anterior': 36066, 'actual': 36972}
    ] 
    
    for d in data:
        aumento_real = (((d['actual'] - d['anterior']) * 100) / d['anterior']) 
        aumento_real = round(aumento_real, 1)
        print(f'Aumento Real para {d['nombre']} >> {aumento_real}%')

@cli.command()
@click.option('--logs', '-l', is_flag=True, default=False)
@click.argument('amount', type=int, required=True)
@click.argument('year', type=click.IntRange(1943, datetime.date.today().year), required=False)
@click.argument('month', type=click.IntRange(1, 12), required=False)

def actualizacion(amount, year, month, logs=False):
    # TODO 
    # Asi como me muestra los delta relativos
    # que me muestre la cantidad de meses que esta yendo hacia atras
    
    # TODO que pasa si me das un mes que no existe ??? como resolvemos eso


    PONDERACION_IPC = 1
    PONDERACION_USD = 0


    if year and month:
        day = ultimo_dia_mes(year, month)
        fecha_inicio = datetime.date(year, month, day)
    else:
        fecha_inicio = None

    ipc = 0
    if PONDERACION_IPC > 0:
        ipc = delta_ipc(fecha_inicio, logs)
        print('Delta IPC >>', ipc)

    usd = 0
    if PONDERACION_USD > 0:
        usd = delta_usd(fecha_inicio, logs)
        print('Delta USD >>', usd)
    
    amount = float(amount)
    print('Nuevo valor >>', formula_actualizacion(amount, ipc, usd, PONDERACION_IPC, PONDERACION_USD))

    # print('Procesando aumentos ... \n\nVALOR >> $', amount, 'INICIO >>', date)

if __name__ == '__main__':
    cli()

