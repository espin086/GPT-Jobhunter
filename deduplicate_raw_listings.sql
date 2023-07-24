CREATE OR REPLACE TABLE `ai-solutions-lab-randd.jobhunter.raw_listings_deduplicated_temp` AS
SELECT
  DISTINCT posted_date,
  LOWER(job_location) AS job_location,
  LOWER(normalized_company_name) AS company_name,
  linkedin_job_url_cleaned AS listing_url,
  linkedin_company_url_cleaned AS company_url,
  LOWER(job_title) AS job_title
FROM
  `ai-solutions-lab-randd.jobhunter.raw_listings`;

-- Delete the destination table if it exists
DELETE FROM `ai-solutions-lab-randd.jobhunter.raw_listings_deduplicated`
WHERE TRUE;

-- Insert the data into the destination table
INSERT INTO `ai-solutions-lab-randd.jobhunter.raw_listings_deduplicated`
SELECT *
FROM `ai-solutions-lab-randd.jobhunter.raw_listings_deduplicated_temp`;

-- Clean up the temporary table
DROP TABLE `ai-solutions-lab-randd.jobhunter.raw_listings_deduplicated_temp`;
