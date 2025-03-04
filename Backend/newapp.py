from flask import Flask, render_template, Response, jsonify
import random
import math
import time
from shapely.geometry import Point, Polygon

app = Flask(__name__)

# Define a more accurate outline of India
india_outline = Polygon([
    (77, 35), (79, 34), (88, 27), (89, 27), (92, 26), (93, 26), (94, 28), (96, 28),
    (97, 25), (99, 22), (97, 20), (95, 15), (91, 12), (87, 8), (85, 8), (82, 10),
    (80, 13), (77, 13), (75, 11), (70, 11), (70, 20), (69, 23), (67, 24), (66, 27),
    (70, 30), (71, 32), (74, 34), (77, 35)
])

# TSP problem setup
num_cities = 20

def generate_city_in_india():
    while True:
        x = random.uniform(67, 97)
        y = random.uniform(8, 35)
        if india_outline.contains(Point(x, y)):
            return (x, y)

cities = [generate_city_in_india() for _ in range(num_cities)]

def distance(city1, city2):
    return math.sqrt((city1[0] - city2[0])**2 + (city1[1] - city2[1])**2)

def total_distance(tour):
    return sum(distance(cities[tour[i]], cities[tour[i-1]]) for i in range(len(tour)))

def generate_svg(solution, title, iteration, best_distance):
    width, height = 400, 400
    
    # Calculate scaling factors
    min_x, min_y = 67, 8
    max_x, max_y = 97, 35
    scale_x = width / (max_x - min_x)
    scale_y = height / (max_y - min_y)
    
    def scale_point(x, y):
        return ((x - min_x) * scale_x, height - (y - min_y) * scale_y)
    
    svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<image href="/static/india_map.png" width="{width}" height="{height}"/>'
    svg += f'<text x="{width/2}" y="20" text-anchor="middle" font-size="16" fill="white">{title}</text>'
    svg += f'<text x="{width/2}" y="{height - 20}" text-anchor="middle" font-size="14" fill="white">Iteration: {iteration}</text>'
    svg += f'<text x="{width/2}" y="{height - 5}" text-anchor="middle" font-size="14" fill="white">Distance: {best_distance:.2f}</text>'

    # Draw path
    path = "M"
    for i in solution:
        x, y = scale_point(*cities[i])
        path += f"{x},{y} "
    path += "Z"
    svg += f'<path d="{path}" fill="none" stroke="red" stroke-width="2"/>'

    # Draw cities
    for i, (x, y) in enumerate(cities):
        sx, sy = scale_point(x, y)
        svg += f'<circle cx="{sx}" cy="{sy}" r="3" fill="yellow"/>'

    svg += '</svg>'
    return svg

def genetic_algorithm():
    population_size = 50
    generations = 100
    population = [random.sample(range(num_cities), num_cities) for _ in range(population_size)]
    best_distance = float('inf')
    best_solution = None
    no_improvement = 0
    start_time = time.time()
    
    for generation in range(generations):
        population = sorted(population, key=total_distance)
        current_best = population[0]
        current_distance = total_distance(current_best)
        
        if current_distance < best_distance:
            best_distance = current_distance
            best_solution = current_best
            no_improvement = 0
        else:
            no_improvement += 1
        
        yield current_best, generation, best_distance
        
        if no_improvement >= 20:  # Stop if no improvement for 20 generations
            break
        
        new_population = population[:population_size//2]
        
        for _ in range(population_size//2):
            parent1, parent2 = random.sample(new_population, 2)
            child = parent1[:num_cities//2] + [city for city in parent2 if city not in parent1[:num_cities//2]]
            new_population.append(child)
        
        population = new_population
        
        # Mutation
        for i in range(1, len(population)):
            if random.random() < 0.1:
                j, k = random.sample(range(num_cities), 2)
                population[i][j], population[i][k] = population[i][k], population[i][j]
    
    end_time = time.time()
    return {
        'algorithm': 'Genetic Algorithm',
        'best_distance': best_distance,
        'iterations': generation + 1,
        'time': end_time - start_time,
        'best_solution': best_solution
    }

def simulated_annealing():
    initial_temp = 1000
    final_temp = 1
    cooling_rate = 0.995
    
    current_solution = list(range(num_cities))
    random.shuffle(current_solution)
    current_distance = total_distance(current_solution)
    best_solution = current_solution[:]
    best_distance = current_distance
    temperature = initial_temp
    
    iteration = 0
    start_time = time.time()
    while temperature > final_temp:
        iteration += 1
        yield best_solution, iteration, best_distance
        
        i, j = random.sample(range(num_cities), 2)
        new_solution = current_solution[:]
        new_solution[i], new_solution[j] = new_solution[j], new_solution[i]
        new_distance = total_distance(new_solution)
        
        if new_distance < current_distance or random.random() < math.exp((current_distance - new_distance) / temperature):
            current_solution = new_solution
            current_distance = new_distance
            
            if current_distance < best_distance:
                best_solution = current_solution[:]
                best_distance = current_distance
        
        temperature *= cooling_rate
    
    end_time = time.time()
    return {
        'algorithm': 'Simulated Annealing',
        'best_distance': best_distance,
        'iterations': iteration,
        'time': end_time - start_time,
        'best_solution': best_solution
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/solve_ga')
def solve_ga():
    def generate():
        for solution, iteration, best_distance in genetic_algorithm():
            svg = generate_svg(solution, "Genetic Algorithm", iteration, best_distance)
            yield f"data: {svg}\n\n"
            time.sleep(0.05)  # Add a small delay to slow down the visualization
    return Response(generate(), mimetype='text/event-stream')

@app.route('/solve_sa')
def solve_sa():
    def generate():
        for solution, iteration, best_distance in simulated_annealing():
            svg = generate_svg(solution, "Simulated Annealing", iteration, best_distance)
            yield f"data: {svg}\n\n"
            time.sleep(0.05)  # Add a small delay to slow down the visualization
    return Response(generate(), mimetype='text/event-stream')

@app.route('/results')
def get_results():
    ga_results = genetic_algorithm()
    sa_results = simulated_annealing()
    
    winner = ga_results if ga_results['best_distance'] < sa_results['best_distance'] else sa_results
    
    return jsonify({
        'ga': ga_results,
        'sa': sa_results,
        'winner': winner['algorithm']
    })

if __name__ == '__main__':
    app.run(debug=True)