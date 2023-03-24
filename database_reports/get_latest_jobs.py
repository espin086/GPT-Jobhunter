import sqlite3
import datetime

import statistics

FILE_PATH = '/Users/jjespinoza/Documents/jobhunter'

conn = sqlite3.connect(f'{FILE_PATH}/database/jobhunter.db')

def get_similarity_stats():
    c = conn.cursor()
    c.execute("SELECT resume_similarity FROM jobs WHERE resume_similarity IS NOT NULL")
    similarities = c.fetchall()
    similarities = [sim[0] for sim in similarities if sim[0] is not None]
    mean_similarity = round(statistics.mean(similarities), 2)
    median_similarity = round(statistics.median(similarities), 2)
    min_similarity = round(min(similarities), 2)
    max_similarity = round(max(similarities), 2)
    q1_similarity = round(statistics.quantiles(similarities, n=4)[0], 2)
    q2_similarity = round(statistics.quantiles(similarities, n=4)[1], 2)
    q3_similarity = round(statistics.quantiles(similarities, n=4)[2], 2)
    return mean_similarity, median_similarity, min_similarity, max_similarity, q1_similarity, q2_similarity, q3_similarity



def print_jobs_sorted(daysback, similarity_threshold):
    # set the current date
    current_date = datetime.date.today()

    # setting how far back to go
    start_date = current_date - datetime.timedelta(days=daysback)
    
    c = conn.cursor()
    c.execute("SELECT date, company, title, resume_similarity, salary_low, salary_high, job_url FROM jobs WHERE date >= ? AND resume_similarity > ? ORDER BY date DESC, resume_similarity DESC", (start_date, similarity_threshold,))
    results = c.fetchall()
    for row in results:
        print("-"*40)
        print("date: " + row[0]) 
        print("company: " + row[1])
        print("title: " + row[2])
        print("similarity: " + str(row[3]))
        print("salary_low: " + str(row[4]))
        print("salary_high: " + str(row[5]))
        print("job_url: " + str(row[6]))
    conn.close()



if __name__ == "__main__":
    mean_similarity, median_similarity, min_similarity, max_similarity, q1_similarity, q2_similarity, q3_similarity = get_similarity_stats()
    print_jobs_sorted(daysback=3, similarity_threshold=min_similarity)
