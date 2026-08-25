/*
  SSMS script — 277 and 999 tables only.

  Every table has:
    id BIGINT IDENTITY(1,1) NOT NULL  — primary key (seed 1, increment 1)
    CreatedUserId INT NOT NULL
    CreatedDateTime DATETIMEOFFSET(7) NOT NULL
    UpdatedDateTime DATETIMEOFFSET(7) NULL
    UpdatedUserId INT NULL
    RecordStatusId INT NOT NULL
    IsDeleted BIT NULL
    RowVersion TIMESTAMP NULL

  Tables created (schema dbo):
    dbo.Edi277File
    dbo.Edi277Status
    dbo.Edi999File
    dbo.Edi999Ack
    dbo.Edi999Ik5ErrorCode
    dbo.Edi999Ak9ErrorCode
    dbo.Edi999Error
    dbo.Edi999ElementError
    dbo.Edi999ErrorContext
    dbo.Edi999AckContext

  Does not drop existing data. Mongo saves stay the same.

  Run in SQL Server Management Studio (F5).
  Database: ClaudMD_Development_Sithum
*/

USE [ClaudMD_Development_Sithum];
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

/* If tables were created under schema edi, drop them so they can be created in dbo. */
IF OBJECT_ID(N'edi.Edi999ElementError', N'U') IS NOT NULL DROP TABLE [edi].[Edi999ElementError];
IF OBJECT_ID(N'edi.Edi999ErrorContext', N'U') IS NOT NULL DROP TABLE [edi].[Edi999ErrorContext];
IF OBJECT_ID(N'edi.Edi999AckContext', N'U') IS NOT NULL DROP TABLE [edi].[Edi999AckContext];
IF OBJECT_ID(N'edi.Edi999Ik5ErrorCode', N'U') IS NOT NULL DROP TABLE [edi].[Edi999Ik5ErrorCode];
IF OBJECT_ID(N'edi.Edi999Ak9ErrorCode', N'U') IS NOT NULL DROP TABLE [edi].[Edi999Ak9ErrorCode];
IF OBJECT_ID(N'edi.Edi999Error', N'U') IS NOT NULL DROP TABLE [edi].[Edi999Error];
IF OBJECT_ID(N'edi.Edi999Ack', N'U') IS NOT NULL DROP TABLE [edi].[Edi999Ack];
IF OBJECT_ID(N'edi.Edi999File', N'U') IS NOT NULL DROP TABLE [edi].[Edi999File];
IF OBJECT_ID(N'edi.Edi277Status', N'U') IS NOT NULL DROP TABLE [edi].[Edi277Status];
IF OBJECT_ID(N'edi.Edi277File', N'U') IS NOT NULL DROP TABLE [edi].[Edi277File];
IF EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'edi')
    AND NOT EXISTS (SELECT 1 FROM sys.objects WHERE schema_id = SCHEMA_ID(N'edi'))
    EXEC(N'DROP SCHEMA [edi]');
GO

/* =====================================================================
   277  (one Mongo document = one Edi277Status row)
   ===================================================================== */

IF OBJECT_ID(N'dbo.Edi277File', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[Edi277File]
    (
        [id]                        BIGINT IDENTITY(1,1) NOT NULL,
        [Source]                    NVARCHAR(50)  NOT NULL,
        [SourceFilename]            NVARCHAR(260) NOT NULL,
        [FileType]                  NVARCHAR(100) NULL,
        [ImportedAt]                DATETIME2(3)  NOT NULL CONSTRAINT [DF_Edi277File_ImportedAt] DEFAULT (SYSUTCDATETIME()),
        [SenderId]                  NVARCHAR(15)  NULL,
        [ReceiverId]                NVARCHAR(15)  NULL,
        [InterchangeDate]           NVARCHAR(20)  NULL,
        [InterchangeTime]           NVARCHAR(10)  NULL,
        [InterchangeVersion]        NVARCHAR(10)  NULL,
        [InterchangeControlNumber]  NVARCHAR(20)  NULL,
        [UsageIndicator]            CHAR(1)       NULL,
        [FunctionalGroup]           NVARCHAR(5)   NULL,
        [ApplicationSender]         NVARCHAR(15)  NULL,
        [ApplicationReceiver]       NVARCHAR(15)  NULL,
        [GroupDate]                 NVARCHAR(20)  NULL,
        [GroupTime]                 NVARCHAR(10)  NULL,
        [GroupControlNumber]        NVARCHAR(20)  NULL,
        [ImplementationVersion]     NVARCHAR(20)  NULL,
        [CreatedUserId]             INT              NOT NULL,
        [CreatedDateTime]           DATETIMEOFFSET(7) NOT NULL CONSTRAINT [DF_Edi277File_CreatedDateTime] DEFAULT (SYSDATETIMEOFFSET()),
        [UpdatedDateTime]           DATETIMEOFFSET(7) NULL,
        [UpdatedUserId]             INT              NULL,
        [RecordStatusId]            INT              NOT NULL,
        [IsDeleted]                 BIT              NULL,
        [RowVersion]                TIMESTAMP        NULL,
        CONSTRAINT [PK_Edi277File] PRIMARY KEY CLUSTERED ([id]),
        CONSTRAINT [UQ_Edi277File_Source_Filename] UNIQUE ([Source], [SourceFilename]),
        CONSTRAINT [CK_Edi277File_UsageIndicator] CHECK ([UsageIndicator] IS NULL OR [UsageIndicator] IN (N'P', N'T'))
    );
END
GO

IF OBJECT_ID(N'dbo.Edi277Status', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[Edi277Status]
    (
        [id]                        BIGINT IDENTITY(1,1) NOT NULL,
        [FileId]                    BIGINT        NOT NULL,
        [RecordIndex]               INT           NOT NULL,
        [TransactionControlNumber]  NVARCHAR(20)  NULL,
        [GroupControlNumber]        NVARCHAR(20)  NULL,
        [TranDate]                  NVARCHAR(30)  NULL,
        [PatientAccNo]              NVARCHAR(50)  NULL,
        [PatientName]               NVARCHAR(200) NULL,
        [PayerName]                 NVARCHAR(200) NULL,
        [SubmitterName]             NVARCHAR(200) NULL,
        [SubmitterEntityId]         NVARCHAR(80)  NULL,
        [ProviderName]              NVARCHAR(200) NULL,
        [ProviderId]                NVARCHAR(80)  NULL,
        [PayerTrace]                NVARCHAR(50)  NULL,
        [ServiceDate]               NVARCHAR(30)  NULL,
        [ReceivedDate]              NVARCHAR(30)  NULL,
        [ProcessDate]               NVARCHAR(30)  NULL,
        [HlId]                      NVARCHAR(12)  NULL,
        [HlParentId]                NVARCHAR(12)  NULL,
        [HlLevelCode]               NVARCHAR(5)   NULL,
        [HlLevelName]               NVARCHAR(80)  NULL,
        [ClaimStatusCatCode]        NVARCHAR(10)  NULL,
        [ClaimStatusCode]           NVARCHAR(10)  NULL,
        [ClaimStatusCodeFull]       NVARCHAR(50)  NULL,
        [RemarkToken]               NVARCHAR(20)  NULL,
        [StatusDate]                NVARCHAR(30)  NULL,
        [StatusQualifier]           NVARCHAR(10)  NULL,
        [StatusAmount]              DECIMAL(18,2) NULL,
        [Status]                    NVARCHAR(50)  NULL,
        [Remarks]                   NVARCHAR(20)  NULL,
        [SubmitterId]               NVARCHAR(80)  NULL,
        [InsuredId]                 NVARCHAR(80)  NULL,
        [CreatedUserId]             INT              NOT NULL,
        [CreatedDateTime]           DATETIMEOFFSET(7) NOT NULL CONSTRAINT [DF_Edi277Status_CreatedDateTime] DEFAULT (SYSDATETIMEOFFSET()),
        [UpdatedDateTime]           DATETIMEOFFSET(7) NULL,
        [UpdatedUserId]             INT              NULL,
        [RecordStatusId]            INT              NOT NULL,
        [IsDeleted]                 BIT              NULL,
        [RowVersion]                TIMESTAMP        NULL,
        CONSTRAINT [PK_Edi277Status] PRIMARY KEY CLUSTERED ([id]),
        CONSTRAINT [UQ_Edi277Status_File_RecordIndex] UNIQUE ([FileId], [RecordIndex]),
        CONSTRAINT [CK_Edi277Status_RecordIndex] CHECK ([RecordIndex] > 0),
        CONSTRAINT [FK_Edi277Status_Edi277File]
            FOREIGN KEY ([FileId]) REFERENCES [dbo].[Edi277File] ([id])
            ON DELETE CASCADE
    );

    CREATE INDEX [IX_Edi277Status_PatientAccNo] ON [dbo].[Edi277Status] ([PatientAccNo]);
    CREATE INDEX [IX_Edi277Status_PayerTrace] ON [dbo].[Edi277Status] ([PayerTrace]);
    CREATE INDEX [IX_Edi277Status_ClaimStatus] ON [dbo].[Edi277Status] ([ClaimStatusCatCode], [ClaimStatusCode]);
END
GO

/* =====================================================================
   999  (one Mongo document = one Edi999Ack row)
   ===================================================================== */

IF OBJECT_ID(N'dbo.Edi999File', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[Edi999File]
    (
        [id]                        BIGINT IDENTITY(1,1) NOT NULL,
        [Source]                    NVARCHAR(50)  NOT NULL,
        [SourceFilename]            NVARCHAR(260) NOT NULL,
        [FileType]                  NVARCHAR(100) NULL,
        [ImportedAt]                DATETIME2(3)  NOT NULL CONSTRAINT [DF_Edi999File_ImportedAt] DEFAULT (SYSUTCDATETIME()),
        [SenderId]                  NVARCHAR(15)  NULL,
        [ReceiverId]                NVARCHAR(15)  NULL,
        [InterchangeDate]           NVARCHAR(20)  NULL,
        [InterchangeTime]           NVARCHAR(10)  NULL,
        [InterchangeVersion]        NVARCHAR(10)  NULL,
        [InterchangeControlNumber]  NVARCHAR(20)  NULL,
        [UsageIndicator]            CHAR(1)       NULL,
        [FunctionalGroup]           NVARCHAR(5)   NULL,
        [ApplicationSender]         NVARCHAR(15)  NULL,
        [ApplicationReceiver]       NVARCHAR(15)  NULL,
        [GroupDate]                 NVARCHAR(20)  NULL,
        [GroupTime]                 NVARCHAR(10)  NULL,
        [GroupControlNumber]        NVARCHAR(20)  NULL,
        [ImplementationVersion]     NVARCHAR(20)  NULL,
        [CreatedUserId]             INT              NOT NULL,
        [CreatedDateTime]           DATETIMEOFFSET(7) NOT NULL CONSTRAINT [DF_Edi999File_CreatedDateTime] DEFAULT (SYSDATETIMEOFFSET()),
        [UpdatedDateTime]           DATETIMEOFFSET(7) NULL,
        [UpdatedUserId]             INT              NULL,
        [RecordStatusId]            INT              NOT NULL,
        [IsDeleted]                 BIT              NULL,
        [RowVersion]                TIMESTAMP        NULL,
        CONSTRAINT [PK_Edi999File] PRIMARY KEY CLUSTERED ([id]),
        CONSTRAINT [UQ_Edi999File_Source_Filename] UNIQUE ([Source], [SourceFilename]),
        CONSTRAINT [CK_Edi999File_UsageIndicator] CHECK ([UsageIndicator] IS NULL OR [UsageIndicator] IN (N'P', N'T'))
    );
END
GO

IF OBJECT_ID(N'dbo.Edi999Ack', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[Edi999Ack]
    (
        [id]                        BIGINT IDENTITY(1,1) NOT NULL,
        [FileId]                    BIGINT        NOT NULL,
        [AckIndex]                  INT           NOT NULL,
        [TransactionControlNumber]  NVARCHAR(20)  NULL,
        [GroupControlNumber]        NVARCHAR(20)  NULL,
        [GroupControlId]            NVARCHAR(20)  NULL,
        [Ak1FunctionalId]           NVARCHAR(5)   NULL,
        [Ak1ImplementationVersion]  NVARCHAR(20)  NULL,
        [AckedFileType]             NVARCHAR(10)  NULL,
        [File837ControlNumber]      NVARCHAR(20)  NULL,
        [Status999]                 NVARCHAR(5)   NULL,
        [OverallStatus999]          NVARCHAR(5)   NULL,
        [Ak9IncludedCount]          INT           NULL,
        [Ak9ReceivedCount]          INT           NULL,
        [Ak9AcceptedCount]          INT           NULL,
        [PatientNo]                 NVARCHAR(50)  NULL,
        [CreatedUserId]             INT              NOT NULL,
        [CreatedDateTime]           DATETIMEOFFSET(7) NOT NULL CONSTRAINT [DF_Edi999Ack_CreatedDateTime] DEFAULT (SYSDATETIMEOFFSET()),
        [UpdatedDateTime]           DATETIMEOFFSET(7) NULL,
        [UpdatedUserId]             INT              NULL,
        [RecordStatusId]            INT              NOT NULL,
        [IsDeleted]                 BIT              NULL,
        [RowVersion]                TIMESTAMP        NULL,
        CONSTRAINT [PK_Edi999Ack] PRIMARY KEY CLUSTERED ([id]),
        CONSTRAINT [UQ_Edi999Ack_File_AckIndex] UNIQUE ([FileId], [AckIndex]),
        CONSTRAINT [CK_Edi999Ack_AckIndex] CHECK ([AckIndex] > 0),
        CONSTRAINT [CK_Edi999Ack_Status999] CHECK (
            [Status999] IS NULL OR [Status999] IN (N'A', N'E', N'R', N'M', N'W', N'X')
        ),
        CONSTRAINT [CK_Edi999Ack_OverallStatus999] CHECK (
            [OverallStatus999] IS NULL OR [OverallStatus999] IN (N'A', N'E', N'P', N'R')
        ),
        CONSTRAINT [FK_Edi999Ack_Edi999File]
            FOREIGN KEY ([FileId]) REFERENCES [dbo].[Edi999File] ([id])
            ON DELETE CASCADE
    );

    CREATE INDEX [IX_Edi999Ack_Status] ON [dbo].[Edi999Ack] ([Status999], [OverallStatus999]);
    CREATE INDEX [IX_Edi999Ack_837Control] ON [dbo].[Edi999Ack] ([File837ControlNumber]);
    CREATE INDEX [IX_Edi999Ack_GroupControlId] ON [dbo].[Edi999Ack] ([GroupControlId]);
END
GO

IF OBJECT_ID(N'dbo.Edi999Ik5ErrorCode', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[Edi999Ik5ErrorCode]
    (
        [id]             BIGINT IDENTITY(1,1) NOT NULL,
        [AckId]          BIGINT       NOT NULL,
        [CodeIndex]      INT          NOT NULL,
        [ErrorCode]      NVARCHAR(10) NOT NULL,
        [CreatedUserId]  INT              NOT NULL,
        [CreatedDateTime] DATETIMEOFFSET(7) NOT NULL CONSTRAINT [DF_Edi999Ik5ErrorCode_CreatedDateTime] DEFAULT (SYSDATETIMEOFFSET()),
        [UpdatedDateTime] DATETIMEOFFSET(7) NULL,
        [UpdatedUserId]  INT              NULL,
        [RecordStatusId] INT              NOT NULL,
        [IsDeleted]      BIT              NULL,
        [RowVersion]     TIMESTAMP        NULL,
        CONSTRAINT [PK_Edi999Ik5ErrorCode] PRIMARY KEY CLUSTERED ([id]),
        CONSTRAINT [UQ_Edi999Ik5ErrorCode_Ack_CodeIndex] UNIQUE ([AckId], [CodeIndex]),
        CONSTRAINT [FK_Edi999Ik5ErrorCode_Edi999Ack]
            FOREIGN KEY ([AckId]) REFERENCES [dbo].[Edi999Ack] ([id])
            ON DELETE CASCADE
    );
END
GO

IF OBJECT_ID(N'dbo.Edi999Ak9ErrorCode', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[Edi999Ak9ErrorCode]
    (
        [id]             BIGINT IDENTITY(1,1) NOT NULL,
        [AckId]          BIGINT       NOT NULL,
        [CodeIndex]      INT          NOT NULL,
        [ErrorCode]      NVARCHAR(10) NOT NULL,
        [CreatedUserId]  INT              NOT NULL,
        [CreatedDateTime] DATETIMEOFFSET(7) NOT NULL CONSTRAINT [DF_Edi999Ak9ErrorCode_CreatedDateTime] DEFAULT (SYSDATETIMEOFFSET()),
        [UpdatedDateTime] DATETIMEOFFSET(7) NULL,
        [UpdatedUserId]  INT              NULL,
        [RecordStatusId] INT              NOT NULL,
        [IsDeleted]      BIT              NULL,
        [RowVersion]     TIMESTAMP        NULL,
        CONSTRAINT [PK_Edi999Ak9ErrorCode] PRIMARY KEY CLUSTERED ([id]),
        CONSTRAINT [UQ_Edi999Ak9ErrorCode_Ack_CodeIndex] UNIQUE ([AckId], [CodeIndex]),
        CONSTRAINT [FK_Edi999Ak9ErrorCode_Edi999Ack]
            FOREIGN KEY ([AckId]) REFERENCES [dbo].[Edi999Ack] ([id])
            ON DELETE CASCADE
    );
END
GO

IF OBJECT_ID(N'dbo.Edi999Error', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[Edi999Error]
    (
        [id]               BIGINT IDENTITY(1,1) NOT NULL,
        [AckId]            BIGINT       NOT NULL,
        [ErrorIndex]       INT          NOT NULL,
        [SegmentId]        NVARCHAR(10) NULL,
        [SegmentPosition]  NVARCHAR(10) NULL,
        [LoopId]           NVARCHAR(20) NULL,
        [ErrorCode]        NVARCHAR(10) NULL,
        [CreatedUserId]    INT              NOT NULL,
        [CreatedDateTime]  DATETIMEOFFSET(7) NOT NULL CONSTRAINT [DF_Edi999Error_CreatedDateTime] DEFAULT (SYSDATETIMEOFFSET()),
        [UpdatedDateTime]  DATETIMEOFFSET(7) NULL,
        [UpdatedUserId]    INT              NULL,
        [RecordStatusId]   INT              NOT NULL,
        [IsDeleted]        BIT              NULL,
        [RowVersion]       TIMESTAMP        NULL,
        CONSTRAINT [PK_Edi999Error] PRIMARY KEY CLUSTERED ([id]),
        CONSTRAINT [UQ_Edi999Error_Ack_ErrorIndex] UNIQUE ([AckId], [ErrorIndex]),
        CONSTRAINT [FK_Edi999Error_Edi999Ack]
            FOREIGN KEY ([AckId]) REFERENCES [dbo].[Edi999Ack] ([id])
            ON DELETE CASCADE
    );
END
GO

IF OBJECT_ID(N'dbo.Edi999ElementError', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[Edi999ElementError]
    (
        [id]               BIGINT IDENTITY(1,1) NOT NULL,
        [ErrorId]          BIGINT        NOT NULL,
        [ElementIndex]     INT           NOT NULL,
        [ElementPosition]  NVARCHAR(20)  NULL,
        [ElementRef]       NVARCHAR(20)  NULL,
        [ErrorCode]        NVARCHAR(10)  NULL,
        [BadData]          NVARCHAR(80)  NULL,
        [CreatedUserId]    INT              NOT NULL,
        [CreatedDateTime]  DATETIMEOFFSET(7) NOT NULL CONSTRAINT [DF_Edi999ElementError_CreatedDateTime] DEFAULT (SYSDATETIMEOFFSET()),
        [UpdatedDateTime]  DATETIMEOFFSET(7) NULL,
        [UpdatedUserId]    INT              NULL,
        [RecordStatusId]   INT              NOT NULL,
        [IsDeleted]        BIT              NULL,
        [RowVersion]       TIMESTAMP        NULL,
        CONSTRAINT [PK_Edi999ElementError] PRIMARY KEY CLUSTERED ([id]),
        CONSTRAINT [UQ_Edi999ElementError_Error_ElementIndex] UNIQUE ([ErrorId], [ElementIndex]),
        CONSTRAINT [FK_Edi999ElementError_Edi999Error]
            FOREIGN KEY ([ErrorId]) REFERENCES [dbo].[Edi999Error] ([id])
            ON DELETE CASCADE
    );
END
GO

IF OBJECT_ID(N'dbo.Edi999ErrorContext', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[Edi999ErrorContext]
    (
        [id]                BIGINT IDENTITY(1,1) NOT NULL,
        [ErrorId]           BIGINT        NOT NULL,
        [ContextIndex]      INT           NOT NULL,
        [ContextName]       NVARCHAR(80)  NULL,
        [SegmentId]         NVARCHAR(10)  NULL,
        [SegmentPosition]   NVARCHAR(10)  NULL,
        [LoopId]            NVARCHAR(20)  NULL,
        [ElementsCsv]       NVARCHAR(400) NULL,
        [CreatedUserId]     INT              NOT NULL,
        [CreatedDateTime]   DATETIMEOFFSET(7) NOT NULL CONSTRAINT [DF_Edi999ErrorContext_CreatedDateTime] DEFAULT (SYSDATETIMEOFFSET()),
        [UpdatedDateTime]   DATETIMEOFFSET(7) NULL,
        [UpdatedUserId]     INT              NULL,
        [RecordStatusId]    INT              NOT NULL,
        [IsDeleted]         BIT              NULL,
        [RowVersion]        TIMESTAMP        NULL,
        CONSTRAINT [PK_Edi999ErrorContext] PRIMARY KEY CLUSTERED ([id]),
        CONSTRAINT [UQ_Edi999ErrorContext_Error_ContextIndex] UNIQUE ([ErrorId], [ContextIndex]),
        CONSTRAINT [FK_Edi999ErrorContext_Edi999Error]
            FOREIGN KEY ([ErrorId]) REFERENCES [dbo].[Edi999Error] ([id])
            ON DELETE CASCADE
    );
END
GO

IF OBJECT_ID(N'dbo.Edi999AckContext', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[Edi999AckContext]
    (
        [id]                BIGINT IDENTITY(1,1) NOT NULL,
        [AckId]             BIGINT        NOT NULL,
        [ContextIndex]      INT           NOT NULL,
        [ContextName]       NVARCHAR(80)  NULL,
        [SegmentId]         NVARCHAR(10)  NULL,
        [SegmentPosition]   NVARCHAR(10)  NULL,
        [LoopId]            NVARCHAR(20)  NULL,
        [ElementsCsv]       NVARCHAR(400) NULL,
        [CreatedUserId]     INT              NOT NULL,
        [CreatedDateTime]   DATETIMEOFFSET(7) NOT NULL CONSTRAINT [DF_Edi999AckContext_CreatedDateTime] DEFAULT (SYSDATETIMEOFFSET()),
        [UpdatedDateTime]   DATETIMEOFFSET(7) NULL,
        [UpdatedUserId]     INT              NULL,
        [RecordStatusId]    INT              NOT NULL,
        [IsDeleted]         BIT              NULL,
        [RowVersion]        TIMESTAMP        NULL,
        CONSTRAINT [PK_Edi999AckContext] PRIMARY KEY CLUSTERED ([id]),
        CONSTRAINT [UQ_Edi999AckContext_Ack_ContextIndex] UNIQUE ([AckId], [ContextIndex]),
        CONSTRAINT [FK_Edi999AckContext_Edi999Ack]
            FOREIGN KEY ([AckId]) REFERENCES [dbo].[Edi999Ack] ([id])
            ON DELETE CASCADE
    );
END
GO

PRINT 'EDI 277/999 SQL tables are ready (schema dbo). Mongo saves were not changed.';
GO
