USE [CycloneRCM_DEV_Ranie]
GO

-- =============================================
-- Combined Script: Drop and Create All Tables
-- Author: Ranie
-- Date: Generated Script
-- Description: Drops and recreates all ClearingHouse tables with foreign keys
-- =============================================

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- =============================================
-- DROP FOREIGN KEY CONSTRAINTS FIRST
-- =============================================

-- Drop foreign keys from ClearingHouse277
IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_ClearingHouse277_ClearingHouseHeader')
    ALTER TABLE [dbo].[ClearingHouse277] DROP CONSTRAINT [FK_ClearingHouse277_ClearingHouseHeader]
GO

-- Drop foreign keys from ClearingHouse999
IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_ClearingHouse999_ClearingHouseHeader')
    ALTER TABLE [dbo].[ClearingHouse999] DROP CONSTRAINT [FK_ClearingHouse999_ClearingHouseHeader]
GO

-- Drop foreign keys from ClearingHouse835Patient
IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_ClearingHouse835Patient_ClearingHouse835Master')
    ALTER TABLE [dbo].[ClearingHouse835Patient] DROP CONSTRAINT [FK_ClearingHouse835Patient_ClearingHouse835Master]
GO

-- Drop foreign keys from ClearingHouse835Service
IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_ClearingHouse835Service_ClearingHouse835Patient')
    ALTER TABLE [dbo].[ClearingHouse835Service] DROP CONSTRAINT [FK_ClearingHouse835Service_ClearingHouse835Patient]
GO

-- Drop foreign keys from ClearingHouse835Adjustment
IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_ClearingHouse835Adjustment_ClearingHouse835Service')
    ALTER TABLE [dbo].[ClearingHouse835Adjustment] DROP CONSTRAINT [FK_ClearingHouse835Adjustment_ClearingHouse835Service]
GO

-- Drop foreign keys from ClearingHouse835ServiceRemark
IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_ClearingHouse835ServiceRemark_ClearingHouse835Service')
    ALTER TABLE [dbo].[ClearingHouse835ServiceRemark] DROP CONSTRAINT [FK_ClearingHouse835ServiceRemark_ClearingHouse835Service]
GO

-- =============================================
-- DROP TABLES
-- =============================================

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ClearingHouse835ServiceRemark]') AND type in (N'U'))
    DROP TABLE [dbo].[ClearingHouse835ServiceRemark]
GO

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ClearingHouse835Adjustment]') AND type in (N'U'))
    DROP TABLE [dbo].[ClearingHouse835Adjustment]
GO

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ClearingHouse835Service]') AND type in (N'U'))
    DROP TABLE [dbo].[ClearingHouse835Service]
GO

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ClearingHouse835Patient]') AND type in (N'U'))
    DROP TABLE [dbo].[ClearingHouse835Patient]
GO

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ClearingHouse835Master]') AND type in (N'U'))
    DROP TABLE [dbo].[ClearingHouse835Master]
GO

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ClearingHouse277]') AND type in (N'U'))
    DROP TABLE [dbo].[ClearingHouse277]
GO

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ClearingHouse999]') AND type in (N'U'))
    DROP TABLE [dbo].[ClearingHouse999]
GO

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ClearingHouseErrorLog]') AND type in (N'U'))
    DROP TABLE [dbo].[ClearingHouseErrorLog]
GO

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ClearingHouseHeader]') AND type in (N'U'))
    DROP TABLE [dbo].[ClearingHouseHeader]
GO

-- =============================================
-- CREATE TABLES
-- =============================================

-- =============================================
-- 1. ClearingHouseHeader (Parent Table - Create First)
-- =============================================
CREATE TABLE [dbo].[ClearingHouseHeader](
	[ClearingHouseHeaderId] [int] IDENTITY(1,1) NOT NULL,
	[FileName] [varchar](500) NOT NULL,
	[FileType] [varchar](10) NOT NULL,
	[ProcessDate] [datetime] NOT NULL,
 CONSTRAINT [PK_ClearingHouseHeader] PRIMARY KEY CLUSTERED 
(
	[ClearingHouseHeaderId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

-- =============================================
-- 2. ClearingHouseErrorLog
-- =============================================
CREATE TABLE [dbo].[ClearingHouseErrorLog](
	[ClearingHouseErrorLogId] [int] IDENTITY(1,1) NOT NULL,
	[FileName] [varchar](500) NOT NULL,
	[FunctionName] [varchar](100) NULL,
	[Error] [varchar](max) NULL,
 CONSTRAINT [PK_ClearingHouseErrorLog] PRIMARY KEY CLUSTERED 
(
	[ClearingHouseErrorLogId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

-- =============================================
-- 3. ClearingHouse277
-- =============================================
CREATE TABLE [dbo].[ClearingHouse277](
	[Id] [int] IDENTITY(1,1) NOT NULL,
	[ClearingHouseHeaderId] [int] NULL,
	[FileName_277] [varchar](500) NOT NULL,
	[GroupControlNumber] [varchar](50) NOT NULL,
	[TranDate] [datetime] NULL,
	[PatientAccNo] [varchar](50) NULL,
	[ClaimStatusCatCode] [varchar](5) NULL,
	[ClaimStatusCode] [varchar](5) NULL,
	[Remarks] [text] NULL,
	[Status] [varchar](5) NULL,
	[Submitter] [varchar](50) NULL,
	[InsuredId] [varchar](50) NULL,
	[ProcessedDateTime] [datetime] NULL,
 CONSTRAINT [PK_ClearingHouse277] PRIMARY KEY CLUSTERED 
(
	[Id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

-- =============================================
-- 4. ClearingHouse999
-- =============================================
CREATE TABLE [dbo].[ClearingHouse999](
	[Id] [int] IDENTITY(1,1) NOT NULL,
	[ClearingHouseHeaderId] [int] NULL,
	[FileName999] [varchar](500) NOT NULL,
	[FileName837] [varchar](500) NULL,
	[GroupControlNumber] [varchar](50) NOT NULL,
	[GroupControlID] [varchar](50) NOT NULL,
	[PatientNo] [varchar](50) NULL,
	[Status999] [varchar](10) NULL,
 CONSTRAINT [PK_ClearingHouse999] PRIMARY KEY CLUSTERED 
(
	[Id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

-- =============================================
-- 5. ClearingHouse835Master
-- =============================================
CREATE TABLE [dbo].[ClearingHouse835Master](
	[ID] [int] IDENTITY(1,1) NOT NULL,
	[ClearingHouseHeaderId] [int] NULL,
	[Filename_835] [varchar](500) NOT NULL,
	[GroupControlNumber] [varchar](50) NOT NULL,
	[Checkdate] [datetime] NULL,
	[CheckNumber] [varchar](50) NULL,
	[TotalPayment] [varchar](50) NULL,
	[Paymentmethod] [varchar](50) NULL,
	[Productiondate] [datetime] NULL,
	[PayerName] [varchar](500) NULL,
	[PayerAddress] [varchar](500) NULL,
	[PayerCity] [varchar](50) NULL,
	[PayerState] [varchar](10) NULL,
	[PayerZipcode] [varchar](10) NULL,
	[Payee] [varchar](500) NULL,
 CONSTRAINT [PK_ClearingHouse835Master] PRIMARY KEY CLUSTERED 
(
	[ID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

-- =============================================
-- 6. ClearingHouse835Patient
-- =============================================
CREATE TABLE [dbo].[ClearingHouse835Patient](
	[ID] [int] IDENTITY(1,1) NOT NULL,
	[ClearingHouse835Id] [int] NOT NULL,
	[PatientAccNo] [varchar](50) NOT NULL,
	[Claimstatuscode] [varchar](50) NULL,
	[TotalClaimChrgAmt] [varchar](50) NULL,
	[ClaimPaymentAmt] [varchar](50) NULL,
	[FacilityTypeCode] [varchar](10) NULL,
	[PayerClaimControlNumber] [varchar](50) NULL,
	[PatientFirstName] [varchar](50) NULL,
	[PatientLastName] [varchar](50) NULL,
 CONSTRAINT [PK_ClearingHouse835Patient] PRIMARY KEY CLUSTERED 
(
	[ID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

-- =============================================
-- 7. ClearingHouse835Service
-- =============================================
CREATE TABLE [dbo].[ClearingHouse835Service](
	[ID] [int] IDENTITY(1,1) NOT NULL,
	[ClearingHouse835PatientId] [int] NOT NULL,
	[ServiceCode] [varchar](50) NOT NULL,
	[ServiceChrgAmt] [varchar](50) NULL,
	[ServiceProviderPayment] [varchar](50) NULL,
	[Units] [int] NULL,
	[ServiceDate] [datetime] NULL,
 CONSTRAINT [PK_ClearingHouse835Service] PRIMARY KEY CLUSTERED 
(
	[ID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

-- =============================================
-- 8. ClearingHouse835Adjustment
-- =============================================
CREATE TABLE [dbo].[ClearingHouse835Adjustment](
	[Id] [int] IDENTITY(1,1) NOT NULL,
	[ClearingHouse835ServiceId] [int] NOT NULL,
	[AdjustmentGroupCode] [varchar](2) NOT NULL,
	[AdjustmentAmount] [varchar](50) NULL,
	[AdjustmentReasonCode] [varchar](10) NULL,
 CONSTRAINT [PK_ClearingHouse835Adjustment] PRIMARY KEY CLUSTERED 
(
	[Id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

-- =============================================
-- 9. ClearingHouse835ServiceRemark
-- =============================================
CREATE TABLE [dbo].[ClearingHouse835ServiceRemark](
	[ID] [int] IDENTITY(1,1) NOT NULL,
	[ClearingHouse835ServiceId] [int] NOT NULL,
	[RemarksCode] [varchar](10) NOT NULL,
 CONSTRAINT [PK_ClearingHouse835ServiceRemark] PRIMARY KEY CLUSTERED 
(
	[ID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

-- =============================================
-- CREATE FOREIGN KEY CONSTRAINTS
-- =============================================

-- Foreign key for ClearingHouse277
ALTER TABLE [dbo].[ClearingHouse277]  WITH CHECK ADD  CONSTRAINT [FK_ClearingHouse277_ClearingHouseHeader] FOREIGN KEY([ClearingHouseHeaderId])
REFERENCES [dbo].[ClearingHouseHeader] ([ClearingHouseHeaderId])
GO

ALTER TABLE [dbo].[ClearingHouse277] CHECK CONSTRAINT [FK_ClearingHouse277_ClearingHouseHeader]
GO

-- Foreign key for ClearingHouse999
ALTER TABLE [dbo].[ClearingHouse999]  WITH CHECK ADD  CONSTRAINT [FK_ClearingHouse999_ClearingHouseHeader] FOREIGN KEY([ClearingHouseHeaderId])
REFERENCES [dbo].[ClearingHouseHeader] ([ClearingHouseHeaderId])
GO

ALTER TABLE [dbo].[ClearingHouse999] CHECK CONSTRAINT [FK_ClearingHouse999_ClearingHouseHeader]
GO

-- Foreign key for ClearingHouse835Patient
ALTER TABLE [dbo].[ClearingHouse835Patient]  WITH CHECK ADD  CONSTRAINT [FK_ClearingHouse835Patient_ClearingHouse835Master] FOREIGN KEY([ClearingHouse835Id])
REFERENCES [dbo].[ClearingHouse835Master] ([ID])
GO

ALTER TABLE [dbo].[ClearingHouse835Patient] CHECK CONSTRAINT [FK_ClearingHouse835Patient_ClearingHouse835Master]
GO

-- Foreign key for ClearingHouse835Service
ALTER TABLE [dbo].[ClearingHouse835Service]  WITH CHECK ADD  CONSTRAINT [FK_ClearingHouse835Service_ClearingHouse835Patient] FOREIGN KEY([ClearingHouse835PatientId])
REFERENCES [dbo].[ClearingHouse835Patient] ([ID])
GO

ALTER TABLE [dbo].[ClearingHouse835Service] CHECK CONSTRAINT [FK_ClearingHouse835Service_ClearingHouse835Patient]
GO

-- Foreign key for ClearingHouse835Adjustment
ALTER TABLE [dbo].[ClearingHouse835Adjustment]  WITH CHECK ADD  CONSTRAINT [FK_ClearingHouse835Adjustment_ClearingHouse835Service] FOREIGN KEY([ClearingHouse835ServiceId])
REFERENCES [dbo].[ClearingHouse835Service] ([ID])
GO

ALTER TABLE [dbo].[ClearingHouse835Adjustment] CHECK CONSTRAINT [FK_ClearingHouse835Adjustment_ClearingHouse835Service]
GO

-- Foreign key for ClearingHouse835ServiceRemark
ALTER TABLE [dbo].[ClearingHouse835ServiceRemark]  WITH CHECK ADD  CONSTRAINT [FK_ClearingHouse835ServiceRemark_ClearingHouse835Service] FOREIGN KEY([ClearingHouse835ServiceId])
REFERENCES [dbo].[ClearingHouse835Service] ([ID])
GO

ALTER TABLE [dbo].[ClearingHouse835ServiceRemark] CHECK CONSTRAINT [FK_ClearingHouse835ServiceRemark_ClearingHouse835Service]
GO


