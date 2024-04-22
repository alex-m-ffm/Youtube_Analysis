import boto3
from datetime import datetime, timedelta
from collections import defaultdict
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    # Initialize DynamoDB client
    dynamodb = boto3.client('dynamodb')

    #retrieve tables from payload
    tables = event.get("tables", [])
    
    # Get the current date and the first day of the current month
    current_date = datetime.now()
    first_day_of_current_month = current_date.replace(day=1)
    
    # Calculate the first day of the previous two months
    first_day_of_previous_month = (first_day_of_current_month - timedelta(days=1)).replace(day=1)
    first_day_of_two_months_ago = (first_day_of_previous_month - timedelta(days=1)).replace(day=1)
    
    # Construct filter expressions for each month
    filter_expression = (
        "begins_with(composite_key, :current_month) OR "
        "begins_with(composite_key, :previous_month) OR "
        "begins_with(composite_key, :two_months_ago)"
    )
    
    # Define expression attribute values for the filter expression
    expression_attribute_values = {
        ":current_month": {"S": current_date.strftime("%Y-%m")},
        ":previous_month": {"S": first_day_of_previous_month.strftime("%Y-%m")},
        ":two_months_ago": {"S": first_day_of_two_months_ago.strftime("%Y-%m")}
    }
        
    for table_name in tables:
        response = dynamodb.scan(
            TableName=table_name,
            FilterExpression=filter_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
    
        # Group items by primary key
        items_by_key = defaultdict(list)
        for item in response['Items']:
            primary_key = item['composite_key']['S']
            sort_key = item['createTime']['S']
            items_by_key[primary_key].append((sort_key, item))
    
        # Iterate over groups of items
        for primary_key, items in items_by_key.items():
            # Sort items by createDate (sortKey)
            items.sort(key=lambda x: x[0], reverse=True)
                
            # Keep only the latest item
            latest_item = items[0][1]
                
            # Delete outdated items (if any)
            for _, item in items[1:]:
                dynamodb.delete_item(
                    TableName=table_name,
                    Key={
                        'composite_key': {'S': primary_key},
                        'createTime': {'S': item['createTime']['S']}
                    }
                )
                logger.info(f"Deleted outdated item with composite key '{primary_key}' and sort key '{item['createTime']['S']}'")
    
        logger.info(f"Clean-up completed successfully for records since {first_day_of_two_months_ago.strftime('%B %Y')} in table {table_name}.")

    return {
        'statusCode': 200,
        'body': 'Cleanup process completed successfully.'
    }