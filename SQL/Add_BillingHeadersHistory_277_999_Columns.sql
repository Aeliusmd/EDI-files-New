/*
  Add 277/999 tracking columns to BillingHeadersHistory
  Database: ClaudMD_Development_Sithum (10.103.0.211)
  Safe: only ADDs nullable columns if missing — no drops, no alters of existing columns.

  Note: 999FileHeader / 277FileHeader tables do not exist on this DB.
  Our EDI file headers live in dbo.Edi999File / dbo.Edi277File.
  Column names follow the ClaudMD spec; IDs are BIGINT to match Edi999File.id / Edi277File.id.
*/

USE [ClaudMD_Development_Sithum];
GO

IF OBJECT_ID(N'dbo.BillingHeadersHistory', N'U') IS NULL
BEGIN
    RAISERROR('dbo.BillingHeadersHistory not found.', 16, 1);
    RETURN;
END
GO

IF COL_LENGTH('dbo.BillingHeadersHistory', '999FileHeaderId') IS NULL
    ALTER TABLE [dbo].[BillingHeadersHistory]
        ADD [999FileHeaderId] BIGINT NULL;
GO

IF COL_LENGTH('dbo.BillingHeadersHistory', '277FileHeaderId') IS NULL
    ALTER TABLE [dbo].[BillingHeadersHistory]
        ADD [277FileHeaderId] BIGINT NULL;
GO

IF COL_LENGTH('dbo.BillingHeadersHistory', 'Is999FileAccepted') IS NULL
    ALTER TABLE [dbo].[BillingHeadersHistory]
        ADD [Is999FileAccepted] BIT NULL;
GO

IF COL_LENGTH('dbo.BillingHeadersHistory', 'Is277FileAccepted') IS NULL
    ALTER TABLE [dbo].[BillingHeadersHistory]
        ADD [Is277FileAccepted] BIT NULL;
GO

IF COL_LENGTH('dbo.BillingHeadersHistory', '999FileAcceptedOrRejectedReason') IS NULL
    ALTER TABLE [dbo].[BillingHeadersHistory]
        ADD [999FileAcceptedOrRejectedReason] NVARCHAR(500) NULL;
GO

IF COL_LENGTH('dbo.BillingHeadersHistory', '277FileAcceptedOrRejectedReason') IS NULL
    ALTER TABLE [dbo].[BillingHeadersHistory]
        ADD [277FileAcceptedOrRejectedReason] NVARCHAR(500) NULL;
GO

/* Optional FK to our Edi file header tables (only if tables exist and FK not already there). */
IF OBJECT_ID(N'dbo.Edi999File', N'U') IS NOT NULL
   AND NOT EXISTS (
       SELECT 1 FROM sys.foreign_keys
       WHERE name = N'FK_BillingHeadersHistory_Edi999File'
   )
BEGIN
    ALTER TABLE [dbo].[BillingHeadersHistory] WITH NOCHECK
        ADD CONSTRAINT [FK_BillingHeadersHistory_Edi999File]
            FOREIGN KEY ([999FileHeaderId]) REFERENCES [dbo].[Edi999File] ([id]);
END
GO

IF OBJECT_ID(N'dbo.Edi277File', N'U') IS NOT NULL
   AND NOT EXISTS (
       SELECT 1 FROM sys.foreign_keys
       WHERE name = N'FK_BillingHeadersHistory_Edi277File'
   )
BEGIN
    ALTER TABLE [dbo].[BillingHeadersHistory] WITH NOCHECK
        ADD CONSTRAINT [FK_BillingHeadersHistory_Edi277File]
            FOREIGN KEY ([277FileHeaderId]) REFERENCES [dbo].[Edi277File] ([id]);
END
GO

PRINT 'BillingHeadersHistory 277/999 columns ready.';
