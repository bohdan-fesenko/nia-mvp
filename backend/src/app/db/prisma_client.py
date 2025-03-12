import logging
import subprocess
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class PrismaClient:
    """
    Python wrapper for Prisma Client JS to interact with the database.
    This class provides methods to execute Prisma operations from Python.
    """
    
    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize the Prisma client wrapper
        
        Args:
            schema_path: Optional path to the Prisma schema file
        """
        self.schema_path = schema_path or str(Path(__file__).parent.parent.parent.parent / "prisma" / "schema.prisma")
        self._ensure_prisma_client_generated()
    
    def _ensure_prisma_client_generated(self):
        """
        Ensure that the Prisma client has been generated
        """
        try:
            # Check if node_modules/.prisma exists
            prisma_dir = Path(__file__).parent.parent.parent.parent / "node_modules" / ".prisma"
            if not prisma_dir.exists():
                logger.info("Generating Prisma client...")
                result = subprocess.run(
                    ["npx", "prisma", "generate"],
                    cwd=str(Path(self.schema_path).parent),
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    logger.error(f"Failed to generate Prisma client: {result.stderr}")
                    raise RuntimeError(f"Failed to generate Prisma client: {result.stderr}")
                logger.info("Prisma client generated successfully")
        except Exception as e:
            logger.error(f"Error ensuring Prisma client is generated: {str(e)}")
            raise
    
    def _execute_prisma_command(self, operation: str, model: str, data: Dict[str, Any] = None, 
                               where: Dict[str, Any] = None, include: Dict[str, Any] = None,
                               order_by: Dict[str, Any] = None, skip: int = None, 
                               take: int = None) -> Dict[str, Any]:
        """
        Execute a Prisma command using Node.js
        
        Args:
            operation: The Prisma operation (findMany, findUnique, create, update, delete)
            model: The model name (e.g., 'User', 'Document')
            data: Data for create/update operations
            where: Filter criteria
            include: Relations to include
            order_by: Sorting criteria
            skip: Number of records to skip
            take: Number of records to take
            
        Returns:
            The result of the Prisma operation
        """
        # Build the Prisma query object
        query = {
            "operation": operation,
            "model": model,
        }
        
        if data is not None:
            query["data"] = data
        
        if where is not None:
            query["where"] = where
            
        if include is not None:
            query["include"] = include
            
        if order_by is not None:
            query["orderBy"] = order_by
            
        if skip is not None:
            query["skip"] = skip
            
        if take is not None:
            query["take"] = take
        
        # Create a temporary script to execute the Prisma query
        script_content = f"""
        const {{ PrismaClient }} = require('@prisma/client');
        const prisma = new PrismaClient();
        
        async function main() {{
            try {{
                const query = {json.dumps(query)};
                let result;
                
                switch(query.operation) {{
                    case 'findMany':
                        result = await prisma[query.model].findMany({{
                            where: query.where,
                            include: query.include,
                            orderBy: query.orderBy,
                            skip: query.skip,
                            take: query.take
                        }});
                        break;
                    case 'findUnique':
                    case 'findFirst':
                        result = await prisma[query.model][query.operation]({{
                            where: query.where,
                            include: query.include
                        }});
                        break;
                    case 'create':
                        result = await prisma[query.model].create({{
                            data: query.data,
                            include: query.include
                        }});
                        break;
                    case 'update':
                        result = await prisma[query.model].update({{
                            where: query.where,
                            data: query.data,
                            include: query.include
                        }});
                        break;
                    case 'delete':
                        result = await prisma[query.model].delete({{
                            where: query.where,
                            include: query.include
                        }});
                        break;
                    case 'count':
                        result = await prisma[query.model].count({{
                            where: query.where
                        }});
                        break;
                    default:
                        throw new Error(`Unsupported operation: ${{query.operation}}`);
                }}
                
                console.log(JSON.stringify(result));
                process.exit(0);
            }} catch (error) {{
                console.error(JSON.stringify({{ error: error.message }}));
                process.exit(1);
            }}
        }}
        
        main()
            .catch(e => {{
                console.error(JSON.stringify({{ error: e.message }}));
                process.exit(1);
            }})
            .finally(async () => {{
                await prisma.$disconnect();
            }});
        """
        
        # Create a temporary directory if it doesn't exist
        temp_dir = Path(__file__).parent / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        # Write the script to a temporary file
        script_path = temp_dir / "prisma_query.js"
        with open(script_path, "w") as f:
            f.write(script_content)
        
        try:
            # Execute the script with Node.js
            result = subprocess.run(
                ["node", str(script_path)],
                cwd=str(Path(self.schema_path).parent.parent),
                capture_output=True,
                text=True
            )
            
            # Clean up the temporary file
            os.remove(script_path)
            
            if result.returncode != 0:
                error_data = json.loads(result.stderr) if result.stderr else {"error": "Unknown error"}
                logger.error(f"Prisma operation failed: {error_data}")
                raise RuntimeError(f"Prisma operation failed: {error_data}")
            
            # Parse and return the result
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Prisma result: {result.stdout}")
            raise RuntimeError(f"Failed to parse Prisma result: {result.stdout}")
        except Exception as e:
            logger.error(f"Error executing Prisma command: {str(e)}")
            raise
    
    # Convenience methods for common operations
    
    def find_many(self, model: str, where: Dict[str, Any] = None, include: Dict[str, Any] = None,
                 order_by: Dict[str, Any] = None, skip: int = None, take: int = None) -> List[Dict[str, Any]]:
        """
        Find multiple records
        """
        return self._execute_prisma_command("findMany", model, where=where, include=include,
                                          order_by=order_by, skip=skip, take=take)
    
    def find_unique(self, model: str, where: Dict[str, Any], include: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Find a unique record
        """
        return self._execute_prisma_command("findUnique", model, where=where, include=include)
    
    def find_first(self, model: str, where: Dict[str, Any] = None, include: Dict[str, Any] = None,
                  order_by: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Find the first record matching the criteria
        """
        return self._execute_prisma_command("findFirst", model, where=where, include=include, order_by=order_by)
    
    def create(self, model: str, data: Dict[str, Any], include: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a new record
        """
        return self._execute_prisma_command("create", model, data=data, include=include)
    
    def update(self, model: str, where: Dict[str, Any], data: Dict[str, Any], 
              include: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Update an existing record
        """
        return self._execute_prisma_command("update", model, where=where, data=data, include=include)
    
    def delete(self, model: str, where: Dict[str, Any], include: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Delete a record
        """
        return self._execute_prisma_command("delete", model, where=where, include=include)
    
    def count(self, model: str, where: Dict[str, Any] = None) -> int:
        """
        Count records matching the criteria
        """
        return self._execute_prisma_command("count", model, where=where)


# Create a singleton instance
prisma_client = PrismaClient()