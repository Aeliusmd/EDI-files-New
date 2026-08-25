/*
  Rename dbo.ERA_* tables to Edi835* (PascalCase),
  same style as dbo.Edi277* and dbo.Edi999*.

  Example: ERA_CLAIM -> Edi835Claim
           ERA_SERVICE_LINE_ADJUSTMENT -> Edi835ServiceLineAdjustment

  Run manually in SSMS (F5).
  Does NOT create or drop tables — rename only.
*/

USE [ClaudMD_Development_Sithum];
GO

/* Child / leaf tables first is safer for readability; sp_rename updates table FKs. */

EXEC sp_rename N'dbo.ERA_CLAIM_ADJUSTMENT',          N'Edi835ClaimAdjustment';
EXEC sp_rename N'dbo.ERA_CLAIM_DATE',                N'Edi835ClaimDate';
EXEC sp_rename N'dbo.ERA_CLAIM_REFERENCE',           N'Edi835ClaimReference';
EXEC sp_rename N'dbo.ERA_CLAIM_REMARK',              N'Edi835ClaimRemark';
EXEC sp_rename N'dbo.ERA_SERVICE_LINE_ADJUSTMENT',   N'Edi835ServiceLineAdjustment';
EXEC sp_rename N'dbo.ERA_SERVICE_LINE_AMOUNT',       N'Edi835ServiceLineAmount';
EXEC sp_rename N'dbo.ERA_SERVICE_LINE_MODIFIER',     N'Edi835ServiceLineModifier';
EXEC sp_rename N'dbo.ERA_SERVICE_LINE_REFERENCE',    N'Edi835ServiceLineReference';
EXEC sp_rename N'dbo.ERA_SERVICE_LINE_REMARK',       N'Edi835ServiceLineRemark';
EXEC sp_rename N'dbo.ERA_INVOICE_FETCH_FAILURE',     N'Edi835InvoiceFetchFailure';
EXEC sp_rename N'dbo.ERA_INVOICE_FETCH_STATUS',      N'Edi835InvoiceFetchStatus';
EXEC sp_rename N'dbo.ERA_INVOICE_MATCH',             N'Edi835InvoiceMatch';
EXEC sp_rename N'dbo.ERA_INVOICE_NUMBER',            N'Edi835InvoiceNumber';
EXEC sp_rename N'dbo.ERA_DATE',                      N'Edi835Date';
EXEC sp_rename N'dbo.ERA_REFERENCE',                 N'Edi835Reference';
EXEC sp_rename N'dbo.ERA_SERVICE_LINE',              N'Edi835ServiceLine';
EXEC sp_rename N'dbo.ERA_CLAIM',                     N'Edi835Claim';
EXEC sp_rename N'dbo.ERA_PAYMENT',                   N'Edi835Payment';
GO

PRINT 'Renamed ERA_* tables to Edi835* in ClaudMD_Development_Sithum.';
GO

/* Quick check */
SELECT s.name AS [schema], t.name AS [table]
FROM sys.tables t
JOIN sys.schemas s ON s.schema_id = t.schema_id
WHERE s.name = N'dbo'
  AND (t.name LIKE N'Edi835%' OR t.name LIKE N'ERA_%')
ORDER BY t.name;
GO
